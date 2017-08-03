#!/usr/bin/env python
import argparse
import sqlite3
import configparser
import datetime
import matplotlib.pyplot as plt
import os.path
import sys
import numpy as np
from decimal import Decimal


def register_bill(config):
    """
    Register a new bill.
    :param config: The configuration to work with
    :return: Nothing.
    """
    # request information
    title = input('Title: ')
    amount = input('Amount: ')
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
                    type=str,
                    nargs='?',
                    const=str(datetime.date.today() - datetime.timedelta(days=30)),
                    help='list all bills since given date (defaults to last 30 days)')
parser.add_argument('--plot',
                    type=str,
                    nargs='?',
                    const=str(datetime.date.today() - datetime.timedelta(days=30)),
                    help='plot monthly histogram of all bills since given date (defaults to last 30 days)')
parser.add_argument('--deficit',
                    type=str,
                    action='store',
                    help='compute current deficit given monthly spending target')
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
    db.execute('CREATE TABLE bills (title text, amount text, date text)')

    # commit and close
    db.commit()
    db.close()

    print('[+] Database initialized.')
elif args.register:
    register_bill(config)
elif args.list is not None:
    # get dates
    today = datetime.date.today()
    begin = args.list

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills WHERE date BETWEEN "{}" AND "{}" ORDER BY date ASC'.format(begin, today))
    print('Period of {} to {}'.format(begin, today))
    print('===================================================')
    print()
    total = Decimal(0)
    for i, row in enumerate(rows):
        title, amount, _ = row
        print('[{}] {}: {}'.format(i+1, title, amount))
        total += Decimal(amount)
    print()
    print('Total amount: {}'.format(total))

    # close connection
    db.close()
elif args.plot is not None:
    # get date
    begin = args.plot

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills where date >= "{}" ORDER BY date ASC'.format(begin))

    # accumulate per month
    values = []
    months = []
    for row in rows:
        _, amount, date = row
        parts = date.split('-')
        month = '{}-{}'.format(parts[0], parts[1])

        if len(months) == 0 or months[-1] != month:
            months.append(month)
            values.append(Decimal(amount))
        else:
            values[-1] += Decimal(amount)

    # plot data
    plt.bar(np.arange(len(months)), values)
    plt.xticks(np.arange(len(months)), months)
    plt.show()

    # close connection
    db.close()
elif args.deficit is not None:
    # get target
    target = Decimal(args.deficit)

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills')

    # accumulate per month
    values = []
    months = []
    for row in rows:
        _, amount, date = row
        parts = date.split('-')
        month = '{}-{}'.format(parts[0], parts[1])

        if len(months) == 0 or months[-1] != month:
            months.append(month)
            values.append(Decimal(amount))
        else:
            values[-1] += Decimal(amount)

    # compute deficits
    deficits = [target - value for value in values]
    total = sum(deficits)

    # plot data
    plt.title('Total deficit: {}'.format(total))
    plt.bar(np.arange(len(months)), deficits)
    plt.xticks(np.arange(len(months)), months)
    plt.show()

    # close connection
    db.close()
else:
    print('Unknown action. Please consult the help text using -h option.')
