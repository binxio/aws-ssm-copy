# aws-ssm-copy-parameters
Copy parameters from a AWS parameter store to another 

## Options
```
usage: aws-ssm-copy [options] PARAMETER [PARAMETER ...]
```

positional arguments::
```
	PARAMETER             source path
```

optional arguments::
```
  -h, --help            show this help message and exit
  --one-level, -1       one-level copy
  --recursive, -r       recursive copy
  --overwrite, -f       existing values
  --keep-going, -k      as much as possible, even after an error
  --dry-run, -N         only show what is to be copied
  --source-region AWS::Region
                        to get the parameters from
  --source-profile NAME
                        to obtain the parameters from
  --region AWS::Region  to copy the parameters to
  --profile NAME        to copy the parameters to
  --target-path NAME    to copy the parameters to
  --key-id ID           to use for parameter values in the destination
  --clear-key-id, -C    clear the kms key id associated with the parameter
```


## Example
Copy all parameters under /dev
```
aws-ssm-copy --profile binx-io --recursive /dev 
```

Read more [about copying aws ssm parameters from one account to another](https://binx.io/blog/2020/12/21/how-to-copy-aws-ssm-parameters-from-one-account-to-another/).
