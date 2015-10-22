#!/bin/env python

from __future__ import print_function

import argparse
import click
import munge
import munge.codec
import munge.codec.all
import os
import peeringdb
from peeringdb import client
from peeringdb.localdb import LocalDB
import pip
from pkg_resources import resource_stream, Requirement
import re
import sys



def install_deps(deps, quiet=True):
    for pkg in deps:
        if pip.main(['install', pkg, '--quiet']):
            # run again to display output
            if not quiet:
                pip.main(['install', pkg])
            raise RuntimeError("failed to install %s" % (pkg,))

def get_deps(typ):
    """ get deps from requirement file of specified type """
    deps=[]
    filename = 'facsimile/requirements-%s.txt' % typ
    with resource_stream(Requirement.parse("peeringdb"), filename) as req:
        for line in req:
            deps.append(line.strip())
    return deps

def dict_prompt(data, key, default=''):
    data[key] = click.prompt(key, default=data.get(key, default))

def db_prompt(data):
    for k in ('host', 'port', 'name', 'user', 'password'):
        dict_prompt(data, k)

@click.group()
@click.version_option()
def cli():
    """
    PeeringDB
    """
    pass

@cli.command()
@click.option('--config', envvar='PEERINGDB_HOME', default='~/.peeringdb')
def conf_write(config):
    """ write config file with defaults """
    cfg = peeringdb.config.get_config(config)
    peeringdb.config.write_config(cfg, config)
    return 0

@cli.command()
@click.option('--config', help='config directory',
    envvar='PEERINGDB_HOME',
    default='~/.peeringdb', prompt='config directory')
@click.option('--database', help='database type for local sync',
    type=click.Choice(['none', 'mysql', 'sqlite3']),
    default='none',
    prompt='database type for local sync (mysql,sqlite3)')
def configure(config, database):
    """ configure peeringdb """
    cfg = peeringdb.config.get_config(config)
    db = {}
    if database != 'none':
        print("enter the database config, blank for engine defaults")
        db['engine'] = database
        if database == 'mysql':
            db_prompt(db)
        elif database == 'sqlite3':
            db['name'] = click.prompt('sqlite filename', default='peeringdb.sqlite3')

    cfg['database'] = db
    peeringdb.config.write_config(cfg, config)
    return 0

@cli.command()
@click.option('--config', envvar='PEERINGDB_HOME', default='~/.peeringdb')
def depcheck(config):
    """ check for dependencies, install if necessary """
    cfg = peeringdb.config.get_config(config)
    engine = cfg.get('database', {}).get('engine')
#    if engine == 'mysql':
#    elif engine == 'sqlite3':
    install_deps(get_deps(engine))
    return 0

@cli.command()
@click.option('--config', envvar='PEERINGDB_HOME', default='~/.peeringdb')
def sync(config):
    """ synchronize to a local database """
    cfg = peeringdb.config.get_config(config)
    db = LocalDB(cfg)
    db.sync()
    return 0

def parse_objid(objid):
    match = re.search('(?P<typ>\w+)[^\d]*(?P<id>\d+)', objid)
    if not match:
        return None
    return (match.group('typ'), match.group('id'))

def try_dump_obj(args):
    res = parse_objid(args.cmd)
    if not res:
        return False

    pdb = client.PeeringDB()
    data = pdb.get(res[0], res[1])
    codec = munge.get_codec(args.output_format)()
    codec.dump(data, sys.stdout)
    return True

#    parser.add_argument('-O', '--output-format', action='store', default='yaml', help='output data format')
#    parser.add_argument('--list-codecs', action='store_true', help='list all available codecs')

