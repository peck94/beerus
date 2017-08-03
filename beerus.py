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
                    action='store_true',
                    help='list all bills')
parser.add_argument('--plot',
                    action='store_true',
                    help='plot monthly histogram of all bills')
parser.add_argument('--deficit',
                    type=str,
                    action='store',
                    help='compute deficit given monthly spending target')
parser.add_argument('--avg',
                    action='store_true',
                    help='average monthly spending')
parser.add_argument('--from',
                    nargs='?',
                    action='store',
                    dest='begin',
                    default=str(datetime.date.today() - datetime.timedelta(days=30)),
                    help='starting date, defaults to 30 days ago')
parser.add_argument('--to',
                    nargs='?',
                    action='store',
                    default=str(datetime.date.today()),
                    help='ending date, defaults to today')
args = parser.parse_args()

# read configuration
config = configparser.ConfigParser()
config.read('beerus.conf')

if args.init:
    """
    Initialize the system.
    This involves creating and formatting the SQLite database which will store the bill data.
    """

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
    """
    Store new bill data.
    """
    register_bill(config)
elif args.list:
    """
    List bills starting from a certain date.
    Also list total amount of money spent as well as monthly average.
    """

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills WHERE date BETWEEN "{}" AND "{}" ORDER BY date ASC'.format(args.begin, args.to))
    print('Period of {} to {}'.format(args.begin, args.to))
    print('===================================================')
    print()
    total = Decimal(0)
    month = None
    months = []
    for i, row in enumerate(rows):
        title, amount, date = row
        print('[{}] {}: {}'.format(i+1, title, amount))
        total += Decimal(amount)

        parts = date.split('-')
        m = '{}-{}'.format(parts[0], parts[1])
        if month is None or month != m:
            month = m
            months.append(Decimal(amount))
        else:
            months[-1] += Decimal(amount)
    print()
    print('Total amount: {}'.format(total))
    print('Monthly average: {}'.format(np.mean(months)))

    # close connection
    db.close()
elif args.plot:
    """
    Plot histograms of monthly bill totals starting from a given date.
    """

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills where date BETWEEN "{}" AND "{}" ORDER BY date ASC'.format(args.begin, args.to))

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
elif args.deficit:
    """
    Compute total deficit given monthly spending target.
    The target is the maximal amount of money we aim to spend per month.
    The deficit is the total amount we need to make up in order to achieve this goal.
    You want the deficit to be at most zero.
    """

    # get target
    target = Decimal(args.deficit)

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills WHERE date BETWEEN "{}" AND "{}" ORDER BY date ASC'.format(args.begin, args.to))

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
    deficits = [value - target for value in values]
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
