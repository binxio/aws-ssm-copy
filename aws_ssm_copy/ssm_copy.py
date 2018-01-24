import sys
import boto3
import json
import argparse
from botocore.exceptions import ClientError


class ParameterCopier(object):
    def __init__(self):
        self.target_profile = None
        self.target_region = None
        self.source_profile = None
        self.source_region = None
        self.source_ssm = None
        self.target_ssm = None
        self.dry_run = False

    def connect_to(self, profile, region):
        kwargs = {}
        if profile is not None:
            kwargs['profile_name'] = profile
        if region is not None:
            kwargs['region_name'] = region
        return boto3.Session(**kwargs)

    def connect_to_source(self, profile, region):
        self.source_ssm = self.connect_to(profile, region).client('ssm')
        self.source_sts = self.connect_to(profile, region).client('sts')

    def connect_to_target(self, profile, region):
        self.target_ssm = self.connect_to(profile, region).client('ssm')
        self.target_sts = self.connect_to(profile, region).client('sts')

    def precondition_check(self):
        source_id = self.source_sts.get_caller_identity()
        target_id = self.target_sts.get_caller_identity()
        if source_id['Account'] == target_id['Account']:
            sys.stderr.write('ERROR: cannot copy into the same AWS account.\n')
            sys.exit(1)

    def load_source_parameters(self, args, recursive, one_level):
        result = {}
        paginator = self.source_ssm.get_paginator('describe_parameters')    

        for arg in args:
            kwargs = {}
            if recursive or one_level:
                option = 'Recursive' if recursive else 'OneLevel'
                kwargs['ParameterFilters'] = [{'Key': 'Path', 'Option': option, 'Values': [arg]}]
            else:
                kwargs['ParameterFilters'] = [{'Key': 'Name', 'Option': 'Equals', 'Values': [arg]}]

            arg_parameters = {}
            for page in paginator.paginate(**kwargs):
                for parameter in page['Parameters']:
                    arg_parameters[parameter['Name']] = parameter

            if len(arg_parameters) == 0:
                sys.stderr.write('ERROR: {} not found.\n'.format(arg))
                sys.exit(1)
            result.update(arg_parameters)
        return result

    def copy(self, args, recursive, one_level, overwrite):
        parameters = self.load_source_parameters(args, recursive, one_level)
        for name in parameters:
            value = self.source_ssm.get_parameter(Name=name, WithDecryption=True)
            parameter = parameters[name]
            parameter['Value'] = value['Parameter']['Value']

            if 'LastModifiedDate' in parameter:
                del parameter['LastModifiedDate']
            if 'LastModifiedUser' in parameter:
                del parameter['LastModifiedUser']
            if 'Version' in parameter:
                del parameter['Version']
            parameter['Overwrite'] = overwrite
            sys.stderr.write('INFO: copying {}\n'.format(name))
            if not self.dry_run:
                value = self.target_ssm.put_parameter(**parameter)

    def main(self):
        parser = argparse.ArgumentParser(description='copy parameter store ')
        parser.add_argument('--one-level', '-1', dest='one_level', action='store_true', help='one-level copy')
        parser.add_argument('--recursive', '-r', dest='recursive', action='store_true', help='recursive copy')
        parser.add_argument('--overwrite', '-f', dest='overwrite', action='store_true', help='existing values')
        parser.add_argument('--dry-run', '-N', dest='dry_run', action='store_true', help='only show what is to be copied')
        parser.add_argument('--source-region', dest='source_region', help='to get the parameters from ', metavar='AWS::Region')
        parser.add_argument('--source-profile', dest='source_profile', help='to obtain the parameters from', metavar='NAME')
        parser.add_argument('--region', dest='target_region', help='to copy the parameters to ', metavar='AWS::Region')
        parser.add_argument('--profile', dest='target_profile', help='to copy the parameters to', metavar='NAME')
        parser.add_argument('parameters', metavar='PARAMETER', type=str, nargs='+', help='source path')
        options = parser.parse_args()

        try:
            self.connect_to_source(options.source_profile, options.source_region) 
            self.connect_to_target(options.target_profile, options.target_region) 
            self.precondition_check()
            self.dry_run = options.dry_run
            self.copy(options.parameters, options.recursive, options.one_level, options.overwrite)
        except ClientError as e:
            sys.stderr.write('ERROR: {}\n'.format(e))
            sys.exit(1)

def main():
    cp = ParameterCopier()
    cp.main()

if __name__ == '__main__':
    main()
