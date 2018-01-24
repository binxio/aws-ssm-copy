include Makefile.mk
USERNAME=mvanholsteijn
NAME=aws-ssm-copy-parameters

do-build:
	python setup.py check
	python setup.py build

push:
	rm -rf dist/*
	python setup.py sdist
	twine upload dist/*

clean:
	python setup.py clean
	rm -rf build/* dist/*

autopep:
	autopep8 --experimental --in-place --max-line-length 132 $(shell find . -name \*.py)

install:
	python setup.py install
