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


# parse arguments
parser = argparse.ArgumentParser(description='Manage paper bills')
parser.add_argument('-register',
                    action='store_true',
                    help='register a bill')
parser.add_argument('-delete',
                    action='store_true',
                    help='delete a bill')
parser.add_argument('-init',
                    action='store_true',
                    help='initialize the system')
parser.add_argument('-list',
                    action='store_true',
                    help='list all bills')
parser.add_argument('-plot',
                    action='store_true',
                    help='plot monthly histogram of all bills')
parser.add_argument('-deficit',
                    type=str,
                    dest='target',
                    action='store',
                    help='compute deficit given monthly spending target')
parser.add_argument('-from',
                    nargs='?',
                    action='store',
                    dest='begin',
                    default=str(datetime.date.today() - datetime.timedelta(days=30)),
                    help='starting date, defaults to 30 days ago')
parser.add_argument('-to',
                    nargs='?',
                    action='store',
                    default=str(datetime.date.today()),
                    help='ending date, defaults to today')
parser.add_argument('-dump',
                    action='store',
                    help='dump the database to a text file')
parser.add_argument('-load',
                    action='store',
                    help='load database dump from file')
args = parser.parse_args()

# read configuration
config = configparser.ConfigParser()
config.read('beerus.conf')

if args.init:
    """
    Initialize the system.
    This involves creating and formatting the SQLite database which will store the bill data.
    """

    print('Setting up the system...')

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
    print('Created SQLite database file.')

    # connect to the database
    db = sqlite3.connect(config['DATABASE']['path'])

    # create table
    db.execute('CREATE TABLE bills (title text, amount text, date text)')

    # commit and close
    db.commit()
    db.close()

    print('Database initialized.')
elif args.register:
    """
    Store new bill data.
    """
    print('Registering new bill')
    print('============================')

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
        db.execute('INSERT INTO bills (title,amount,date) VALUES (?, ?, ?)', (title, amount, time))

        # commit the transaction and close it
        db.commit()
        db.close()

        print('Registration completed.')
    else:
        print('Registration aborted.')
elif args.delete:
    """
    Delete a bill from the database.
    """
    print('Deleting existing bill')
    print('============================')

    # request information
    title = input('Title: ')
    amount = input('Amount: ')
    time = input('Date (YYYY-MM-DD, defaults to today): ') or str(datetime.date.today())
    print()

    # verify information
    print('Deleting "{}", amount {}, on {}.'.format(title, amount, time))
    response = input('OK? [Y/n] ')

    if response == 'Y':
        # connect to the database
        db = sqlite3.connect(config['DATABASE']['path'])

        # delete the data
        db.execute('DELETE FROM bills WHERE title = ? AND amount = ? AND date = ?', (title, amount, time))

        # commit and close
        db.commit()
        db.close()

        print('Data deleted.')
    else:
        print('Deletion aborted.')

elif args.list:
    """
    List bills starting from a certain date.
    Also list total amount of money spent as well as monthly average.
    """

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills WHERE date BETWEEN ? AND ? ORDER BY date ASC', (args.begin, args.to))
    row_format = '{:<5}{:<15}{:<15}{:<15}'
    print('Period of {} to {}'.format(args.begin, args.to))
    print('===================================================')
    print(row_format.format('No.', 'Title', 'Amount', 'Date'))
    total = Decimal(0)
    month = None
    months = []
    for i, row in enumerate(rows):
        title, amount, date = row
        print(row_format.format(i+1, title, amount, date))
        total += Decimal(amount)

        parts = date.split('-')
        m = '{}-{}'.format(parts[0], parts[1])
        if month is None or month != m:
            month = m
            months.append(Decimal(amount))
        else:
            months[-1] += Decimal(amount)
    print('===================================================')
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
    rows = db.execute('SELECT * FROM bills where date BETWEEN ? AND ? ORDER BY date ASC', (args.begin, args.to))

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
    plt.title('From {} to {}'.format(args.begin, args.to))
    plt.bar(np.arange(len(months)), values)
    plt.xticks(np.arange(len(months)), months)
    plt.show()

    # close connection
    db.close()
elif args.target:
    """
    Compute total deficit given monthly spending target.
    The target is the maximal amount of money we aim to spend per month.
    The deficit is the total amount we need to make up in order to achieve this goal.
    You want the deficit to be at most zero.
    """

    # get target
    target = Decimal(args.target)

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # query records
    rows = db.execute('SELECT * FROM bills WHERE date BETWEEN ? AND ? ORDER BY date ASC', (args.begin, args.to))

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
elif args.dump is not None:
    print('Dumping database to {}...'.format(args.dump))

    # check if file already exists
    if os.path.isfile(args.dump):
        print('Warning: file already exists.')
        response = input('Overwrite? [Y/n] ')
        if response != 'Y':
            print('Dump aborted.')
            sys.exit(0)

    # connect to db
    db = sqlite3.connect(config['DATABASE']['path'])

    # dump db
    with open(args.dump, 'w') as f:
        for line in db.iterdump():
            f.write('{}\n'.format(line))

    # close db
    db.close()

    print('Done.')
elif args.load is not None:
    print('Loading file {}...'.format(args.load))

    # load file SQL
    with open(args.load, 'r') as f:
        sql = f.read()

    # check if database file exists
    if not os.path.isfile(config['DATABASE']['path']):
        f = open(config['DATABASE']['path'], 'w')
        f.close()

    # connect to database
    db = sqlite3.connect(config['DATABASE']['path'])

    # execute the script
    db.executescript(sql)

    # close the connection
    db.close()

    print('Done.')
else:
    print('Unknown action. Please consult the help text using -h option.')
