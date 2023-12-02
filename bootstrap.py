#!/usr/bin/env python3

from abc import ABC
import argparse
import logging
import os
from pathlib import Path
import subprocess
from pydantic import BaseModel


# path of this file
BASE_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = Path(BASE_DIR, 'configs')
PROFILES_DIR = Path(BASE_DIR, 'profiles')

class Args(BaseModel):
	configs: list[Path] = []
	profiles: list[Path] = []
	dry_run: bool = False
	package_update: bool = True

def main(args: Args):
	profiles = [ _Profile.read(p) for p in args.profiles ]
	configs: list[Path] = _dedup_list(
		[ c for p in profiles for c in p.configs() ]
		+ args.configs
	)

	if args.dry_run:
		print('Configs:')
		for c in configs:
			logging.info(f'\t{c.resolve().as_posix()}')
		return

	# Loading packages here is useful so not each config has to do it
	if args.package_update:
		logging.info('Updating packages...')
		_OsPackageManager.instance().update()

	Dotbot.install_config(*configs)

def _dedup_list(l: list) -> list:
	return list(dict.fromkeys(l))

class Dotbot:
	''' Wrapper for dotbot '''
	pass

	@staticmethod
	def install_config(*configs: Path):
		for c in configs:
			try:
				cmd = [
					'dotbot',
					'--exit-on-failure'
					'--config-file', c.as_posix()
				]
				subprocess.run(*cmd, check=True)
			except subprocess.CalledProcessError as e:
				return
			except Exception as e:
				logging.exception(f'Error executing dotbot: {cmd.join(" ")}')

class _Profile(list):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	@classmethod
	def read(cls, path: Path):
		with open(path, 'r') as f:
			return cls([ line for line in f.readlines() if line.strip() and not line.strip().startswith('#') ])

	def configs(self):
		''' Return paths for all contained configs, preserving order & removing dups '''
		for line in _dedup_list(self):
			yield Path(CONFIGS_DIR, line.strip())

class _OsPackageManager(ABC):
	sudo: str = 'sudo' if os.geteuid() != 0 else ''

	@classmethod
	def instance() -> '_OsPackageManager':
		if os.name == 'posix':
			return _AptGet()
		else:
			raise NotImplementedError()

	def update():
		raise NotImplementedError()

class _AptGet(_OsPackageManager):

	@classmethod
	def update(cls) -> subprocess.CompletedProcess:
		cmd = f'{cls.sudo} apt-get update'
		return subprocess.run(cmd.split(), check=True)

if __name__ == '__main__':
	argparser = argparse.ArgumentParser()
	argparser.add_argument('--configs', type=Path, nargs=argparse.ONE_OR_MORE, default=[])
	argparser.add_argument('--profiles', type=Path, nargs=argparse.ONE_OR_MORE, default=[])
	argparser.add_argument('--dry-run', action='store_true')
	argparser.add_argument('--no-package-update', action='store_false', dest='package_update')
	args = Args(**vars(argparser.parse_args()))
	main(args)
