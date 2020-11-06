from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from time import sleep, time
from random import uniform, randint
import requests
import bs4
import re
import logging
import configparser
import csv
from playsound import playsound
import os
import datetime
from unidecode import unidecode



CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
input_file = os.path.join(CURRENT_DIRECTORY, 'clients.csv')

with open(input_file, mode='r') as f:
    reader = csv.DictReader(f)
    clients = [row for row in reader]

print(clients)

for i, c in enumerate(clients):
    if c['is_done'] == 'FALSE':
        continue

    if randint(1,10) > 3:
        clients[i]['result'] = 'oh yeah'
        clients[i]['is_done'] = 'TRUE'
        keys = clients[0].keys()
        with open('test.csv', 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(clients)


print(clients)