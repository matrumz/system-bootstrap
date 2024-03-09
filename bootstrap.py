#!/usr/bin/env python3

from abc import ABC
import argparse
from collections import OrderedDict
import logging
import os
from pathlib import Path
import subprocess
from pydantic import BaseModel


logging.basicConfig(
	level=logging.INFO,
	format='BOOTSTRAP.PY %(levelname)s: %(message)s'
)

# path of this file
BASE_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = Path(BASE_DIR, 'configs')
PROFILES_DIR = Path(BASE_DIR, 'profiles')

class Args(BaseModel):
	configs: list[Path] = []
	profiles: list[Path] = []
	dry_run: bool = False
	package_update: bool = True
	dotbot_args: list[str] = []

def main(args: Args) -> int:

	# Gather list of configs to install
	profiles = [ _Profile.read(p) for p in args.profiles ]
	configs: list[Path] = _dedup_list(
		[ c for p in profiles for c in p.configs() ]
		+ [ c.resolve() for c in args.configs ]
	)

	# Ensure all configs exist with either .yml or .yaml extension
	# Otherwise list missing configs and exit
	missing_configs = [ c for c in configs if not c.exists() or not c.is_file() or not c.suffix in ['.yml', '.yaml'] ]
	if missing_configs:
		logging.error('Missing configs:')
		for c in missing_configs:
			logging.error(f'\t{c.as_posix()}')
		return 1

	if args.dry_run:
		logging.info('Configs:')
		for c in configs:
			logging.info(f'\t{c.as_posix()}')
		return 0

	# Loading packages here is useful so not each config has to do it
	if args.package_update:
		logging.info('Updating packages...')
		_OsPackageManager.instance().update()

	Dotbot.install_config(*configs)

	return 0

def _dedup_list(l: list) -> list:
	return list(OrderedDict.fromkeys(l))

class Dotbot:
	''' Wrapper for dotbot '''
	pass

	@staticmethod
	def install_config(*configs: Path):
		for c in configs:
			try:
				logging.info(f'Installing config: {c.as_posix()}')
				cmd = [
					'dotbot',
					'--exit-on-failure',
					'--base-directory', BASE_DIR.as_posix(),
					'--config-file', c.as_posix()
				]
				subprocess.run(cmd, check=True)
			except subprocess.CalledProcessError:
				return
			except Exception:
				logging.exception(f'Error executing dotbot: {" ".join(cmd)}')

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
			yield Path(CONFIGS_DIR, line.strip() + '.yaml')

class _OsPackageManager(ABC):
	sudo: str = 'sudo' if os.geteuid() != 0 else ''

	@staticmethod
	def instance() -> '_OsPackageManager':
		if os.name == 'posix':
			return _AptGet()
		else:
			raise NotImplementedError()

	@staticmethod
	def update():
		raise NotImplementedError()

class _AptGet(_OsPackageManager):

	@classmethod
	def update(cls) -> subprocess.CompletedProcess:
		cmd = f'{cls.sudo} apt-get update'
		return subprocess.run(cmd.split(), check=True)

if __name__ == '__main__':
	try:
		argparser = argparse.ArgumentParser()
		argparser.add_argument('--configs', type=Path, nargs=argparse.ONE_OR_MORE, default=[])
		argparser.add_argument('--profiles', type=Path, nargs=argparse.ONE_OR_MORE, default=[])
		argparser.add_argument('--dry-run', action='store_true')
		argparser.add_argument('--no-package-update', action='store_false', dest='package_update')
		args = Args(**vars(argparser.parse_args()))
		exit(main(args))
	except KeyboardInterrupt:
		logging.warning('Interrupted by user')
		exit(1)
	except Exception:
		logging.exception('Unhandled exception')
		exit(1)
	else:
		exit(0)
