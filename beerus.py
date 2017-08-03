#!/usr/bin/env python
import argparse
import sqlite3
import configparser
import datetime
import os
import os.path
import sys


def register_bill(config):
    """
    Register a new bill.
    :param config: The configuration to work with
    :return: Nothing.
    """
    # request information
    title = input('Title: ')
    amount = float(input('Amount: '))
    time = input('Date (YYYY-MM-DD, defaults to today): ') or str(datetime.date.today())
    print()

    # verify information
    print('Registering "{}", amount {}, on {}.'.format(title, amount, time))
    response = input('OK? [Y/n] ')

    if response == 'Y':
        # connect to the database
        db = sqlite3.connect(config['DATABASE']['path'])

        # insert the data
        db.execute('INSERT INTO bills (title,amount,date) VALUES ("{}","{}","{}")'.format(title, amount, time))

        # commit the transaction and close it
        db.commit()
        db.close()
    else:
        print('Registration aborted.')


# parse arguments
parser = argparse.ArgumentParser(description='Manage paper bills')
parser.add_argument('--register',
                    action='store_true',
                    help='register a bill')
parser.add_argument('--init',
                    action='store_true',
                    help='initialize the system')
parser.add_argument('--list',
                    action='store_true',
                    help='list all bills since given date (defaults to last 30 days)')
args = parser.parse_args()

# read configuration
config = configparser.ConfigParser()
config.read('beerus.conf')

if args.init:
    print('[*] Setting up the system...')

    # check if database exists
    if os.path.isfile(config['DATABASE']['path']):
        print('Warning: a database already exists. This action will delete it.')
        response = input('OK? [Y/n] ')
        if response != 'Y':
            print('Action aborted.')
            sys.exit(0)
        else:
            # delete the database
            os.unlink(config['DATABASE']['path'])

    # create database file
    file = open(config['DATABASE']['path'], 'w')
    file.close()
    print('[+] Created SQLite database file.')

    # connect to the database
    db = sqlite3.connect(config['DATABASE']['path'])

    # create table
    db.execute('CREATE TABLE bills (title text, amount float, date text)')

    # commit and close
    db.commit()
    db.close()

    print('[+] Database initialized.')
elif args.register:
    register_bill(config)
elif args.list:
    # last 30 days
    today = datetime.date.today()
    begin = today -  datetime.timedelta(days=30)

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills WHERE date BETWEEN "{}" AND "{}"'.format(begin, today))
    print('Period of {} to {}'.format(today, begin))
    print('===================================================')
    print()
    total = 0
    for i, row in enumerate(rows):
        title, amount, _ = row
        print('[{}] {}: {}'.format(i+1, title, amount))
        total += amount
    print()
    print('Total amount: {}'.format(total))
else:
    print('Unknown action. Please consult the help text using -h option.')
