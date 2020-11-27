import argparse
import re
import sys

import boto3
from botocore.exceptions import ClientError


def rename_parameter(parameter, source_path, target_path):
    """
    >>> rename_parameter({'Name':'/old-root/my-param'}, 'old-root', 'new-root')
    {'Name': '/new-root/my-param'}
    >>> rename_parameter({'Name':'/old-root/my-param'}, '/old-root', '/new-root')
    {'Name': '/new-root/my-param'}
    >>> rename_parameter({'Name':'old-root/my-param'}, '/old-root', '/new-root')
    {'Name': '/new-root/my-param'}
    >>> rename_parameter({'Name':'/old-root/my-param'}, '/invalid-root', '/new-root')
    {'Name': '/old-root/my-param'}
    >>> rename_parameter({'Name':'/old-root/my-param'}, '/old-root', None)
    {'Name': '/old-root/my-param'}
    >>> rename_parameter({'Name':'my-param'}, "/", "/new-root")
    {'Name': '/new-root/my-param'}
    >>> rename_parameter({'Name':'old-root/my-param'}, '/old-root', 'new-root')
    {'Name': '/new-root/my-param'}
    >>> rename_parameter({'Name':'/old-root-not/my-param'}, 'old-root', 'new-root')
    {'Name': '/old-root-not/my-param'}

    """
    result = parameter.copy()
    if not target_path:
        return result

    sp = source_path.strip("/")
    tp = target_path.strip("/")

    if sp == "":
        regex = r"^/?"
    else:
        regex = r"^/?" + sp + "/"

    result["Name"] = re.sub(regex, f"/{tp}/", parameter["Name"])

    return result


class ParameterCopier(object):
    def __init__(self):
        self.target_profile = None
        self.target_region = None
        self.source_profile = None
        self.source_region = None
        self.source_ssm = None
        self.source_sts = None
        self.target_ssm = None
        self.target_sts = None
        self.target_path = None
        self.dry_run = False

    @staticmethod
    def connect_to(profile, region):
        kwargs = {}
        if profile is not None:
            kwargs["profile_name"] = profile
        if region is not None:
            kwargs["region_name"] = region
        return boto3.Session(**kwargs)

    def connect_to_source(self, profile, region):
        self.source_ssm = self.connect_to(profile, region).client("ssm")
        self.source_sts = self.connect_to(profile, region).client("sts")

    def connect_to_target(self, profile, region):
        self.target_ssm = self.connect_to(profile, region).client("ssm")
        self.target_sts = self.connect_to(profile, region).client("sts")

    def load_source_parameters(self, arg, recursive, one_level):
        result = {}
        paginator = self.source_ssm.get_paginator("describe_parameters")
        kwargs = {}
        if recursive or one_level:
            option = "Recursive" if recursive else "OneLevel"
            kwargs["ParameterFilters"] = [
                {"Key": "Path", "Option": option, "Values": [arg]}
            ]
        else:
            kwargs["ParameterFilters"] = [
                {"Key": "Name", "Option": "Equals", "Values": [arg]}
            ]

        for page in paginator.paginate(**kwargs):
            for parameter in page["Parameters"]:
                result[parameter["Name"]] = parameter

        if len(result) == 0:
            sys.stderr.write("ERROR: {} not found.\n".format(arg))
            sys.exit(1)
        return result

    def copy(self, args, recursive, one_level, overwrite, key_id=None, clear_kms_key=False, keep_going=False):
        for arg in args:
            parameters = self.load_source_parameters(arg, recursive, one_level)
            for name in parameters:
                value = self.source_ssm.get_parameter(Name=name, WithDecryption=True)
                parameter = parameters[name]
                parameter["Value"] = value["Parameter"]["Value"]

                if "KeyId" in parameter and key_id is not None:
                    parameter["KeyId"] = key_id
                if "KeyId" in parameter and clear_kms_key:
                    del parameter["KeyId"]
                if "LastModifiedDate" in parameter:
                    del parameter["LastModifiedDate"]
                if "LastModifiedUser" in parameter:
                    del parameter["LastModifiedUser"]
                if "Version" in parameter:
                    del parameter["Version"]
                if "Policies" in parameter:
                    if not parameter["Policies"]:
                        # an empty policies list causes an exception
                        del parameter["Policies"]
                parameter["Overwrite"] = overwrite
                parameter = rename_parameter(parameter, arg, self.target_path)
                new_name = parameter["Name"]
                if self.dry_run:
                    sys.stdout.write(
                        f"DRY-RUN: copying {name} to {new_name}\n"
                    )
                else:

                    try:
                        self.target_ssm.put_parameter(**parameter)
                        sys.stdout.write(
                            f"INFO: copied {name} to {new_name}\n"
                        )
                    except self.target_ssm.exceptions.ParameterAlreadyExists as e:
                        if not keep_going:
                            sys.stderr.write(f"ERROR: failed to copy {name} to {new_name} as it already exists: specify --overwrite or --keep-going\n")
                            exit(1)
                        else:
                            sys.stderr.write(f"WARN: skipping copy {name} as {new_name} already exists\n")
                    except ClientError as e:
                        msg = e.response["Error"]["Message"]
                        sys.stderr.write(f"ERROR: failed to copy {name} to {new_name}, {msg}\n")
                        if not keep_going:
                            exit(1)

    def main(self):
        parser = argparse.ArgumentParser(description="copy parameter store ")
        parser.add_argument(
            "--one-level",
            "-1",
            dest="one_level",
            action="store_true",
            help="one-level copy",
        )
        parser.add_argument(
            "--recursive",
            "-r",
            dest="recursive",
            action="store_true",
            help="recursive copy",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--overwrite",
            "-f",
            dest="overwrite",
            action="store_true",
            help="existing values",
        )
        group.add_argument(
            "--keep-going",
            "-k",
            dest="keep_going",
            action="store_true",
            help="as much as possible after an error",
        )

        parser.add_argument(
            "--dry-run",
            "-N",
            dest="dry_run",
            action="store_true",
            help="only show what is to be copied",
        )
        parser.add_argument(
            "--source-region",
            dest="source_region",
            help="to get the parameters from ",
            metavar="AWS::Region",
        )
        parser.add_argument(
            "--source-profile",
            dest="source_profile",
            help="to obtain the parameters from",
            metavar="NAME",
        )
        parser.add_argument(
            "--region",
            dest="target_region",
            help="to copy the parameters to ",
            metavar="AWS::Region",
        )
        parser.add_argument(
            "--profile",
            dest="target_profile",
            help="to copy the parameters to",
            metavar="NAME",
        )
        parser.add_argument(
            "--target-path",
            dest="target_path",
            help="to copy the parameters to",
            metavar="NAME",
        )
        key_group = parser.add_mutually_exclusive_group()
        key_group.add_argument(
            "--key-id",
            dest="key_id",
            help="to use for parameter values in the destination",
            metavar="ID"
        )
        key_group.add_argument(
            "--clear-key-id",
            "-C",
            dest="clear_key_id",
            action="store_true",
            help="clear the KMS key id associated with the parameter",
        )
        parser.add_argument(
            "parameters", metavar="PARAMETER", type=str, nargs="+", help="source path"
        )
        options = parser.parse_args()

        try:
            self.connect_to_source(options.source_profile, options.source_region)
            self.connect_to_target(options.target_profile, options.target_region)
            self.target_path = options.target_path
            self.dry_run = options.dry_run
            self.copy(
                options.parameters,
                options.recursive,
                options.one_level,
                options.overwrite,
                options.key_id,
                options.clear_key_id,
                options.keep_going,
            )
        except ClientError as e:
            sys.stderr.write("ERROR: {}\n".format(e))
            sys.exit(1)


def main():
    cp = ParameterCopier()
    cp.main()


if __name__ == "__main__":
    main()
