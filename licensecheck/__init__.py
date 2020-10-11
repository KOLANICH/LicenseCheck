"""Output the licenses used by dependencies and check if these are compatible
with the project license
"""
from __future__ import annotations

import subprocess
import argparse
from sys import exit as sysexit, stdout
from shlex import split
import warnings

import requirements

from licensecheck import packageinfo, license_matrix, formatter
from licensecheck.packagecompat import PackageCompat


def _doSysExec(command: str) -> tuple[int, str]:
	"""execute a command and check for errors
	shlex.split can be used to make this safer.
	see https://docs.python.org/3/library/shlex.html#shlex.quote
	Note however, that we can still call _doSysExec with a malicious command
	but this change mitigates command chaining. Ultimately, do not accept user
	input or if you do, escape with shlex.quote(), shlex.join(shlex.split())

	Args:
		command (str): commands as a string

	Raises:
		RuntimeWarning: throw a warning should there be a non exit code
	"""
	with subprocess.Popen(split(command), shell=True, stdout=subprocess.PIPE,
	stderr=subprocess.STDOUT, universal_newlines=True) as process:
		out = process.communicate()[0]
		exitCode = process.returncode
	return exitCode, out


def getdepsLicenses() -> list[PackageCompat]:
	"""Get a list of packages with package compatibility

	Returns:
		list[PackageCompat]: list of packages (python dicts)
	"""
	# Is poetry installed?
	poetryInstalled = True
	if _doSysExec("poetry -h")[0] != 0:
		poetryInstalled = False
		warnings.warn(RuntimeWarning("poetry is not on the system path"))
	# Get list of requirements
	reqs = []
	if poetryInstalled:
		# Use poetry show to get dependents of dependencies
		lines = _doSysExec("poetry show")[1].splitlines(False)
		for line in lines:
			parts = line.split()
			reqs.append(parts[0])
	else:
		with open("requirements.txt", 'r') as requirementsTxt:
			for req in requirements.parse(requirementsTxt): # type: ignore
				reqs.append(req.name) # type: ignore
	# Get my license
	myLiceTxt = packageinfo.getMyPackageLicense()
	myLice = license_matrix.licenseType(myLiceTxt)[0]
	# Check it is compatible with packages and add a note
	depsLicenses = []
	for package in packageinfo.getPackages(reqs):
		depLice = license_matrix.licenseType(package["license"])
		depsLicenses.append(PackageCompat(**package,
		license_compat=license_matrix.depCompatibleLice(myLice, depLice)))
	return depsLicenses

FORMAT_HELP = "Output format. One of simple, ansi, json, markdown, csv. default=simple"

def cli() -> None:
	""" cli entry point """
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--format", "-f", help=FORMAT_HELP)
	parser.add_argument("--file", "-o",
	help="Filename to write to (omit for stdout)")
	args = parser.parse_args()
	# File
	filename = stdout if args.file is None else open(args.file, "w")
	# Format
	formatMap = {
	"json": formatter.json, "markdown": formatter.markdown, "csv": formatter.csv,
	"ansi": formatter.ansi, "simple": formatter.simple}
	if args.format is None:
		print(formatter.simple(getdepsLicenses()), file=filename)
	elif args.format in formatMap:
		print(formatMap[args.format](getdepsLicenses()), file=filename)
	else:
		print(FORMAT_HELP)
		sysexit(1)