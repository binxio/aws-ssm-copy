A simple command line utility to copy AWS parameter store parameters to another account.


**Options**::
	usage: aws-ssm-copy [options] PARAMETER [PARAMETER ...]

positional arguments::
	PARAMETER             source path

optional arguments::
	-h, --help            show this help message and exit
	--one-level, -1       one-level copy
	--recursive, -r       recursive copy
	--overwrite, -f       existing values
	--dry-run, -N         only show what is to be copied
	--source-region AWS::Region
			to get the parameters from
	--source-profile NAME
			to obtain the parameters from
	--region AWS::Region  to copy the parameters to
	--profile NAME        to copy the parameters to
	--target-path NAME    to copy the parameters to


**Example**
Copy all parameters under /dev::

	aws-ssm-copy --profile binx-io --recursive /dev 
