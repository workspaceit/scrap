import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import hashlib
import math
import json
from StringIO import StringIO

import selenium.webdriver as webdriver
import contextlib
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import sys

import unittest, time, re

phantomjs = 'phantomjs'
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.express.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
site_id = 19
brand_id = 424

def get_price(price):
    price_str = ''
    for char in price:
        if char.isnumeric() or char == '.':
            price_str = price_str + char
    return price_str


def is_product_exists(product_id, site_id):
    sql = "SELECT * FROM products WHERE identifier ={0} and site_id={1}"
    sql = sql.format(product_id, site_id)
    cursor.execute(sql)
    data = cursor.fetchall()
    if len(data) == 0:
        return False
    else:
        return True


def get_brand_or_create(brand):
    print "::::::Brand :" + brand + "::::::"
    sql = "SELECT * FROM brands WHERE name ='%s'"
    cursor.execute(sql % brand)
    data = cursor.fetchall()

    if len(data) > 0:
        brand_id = data[0][0]
    else:
        brandSql = "INSERT INTO brands(name) VALUES ('%s')" % (brand)
        brand_id = excute_insert_query(brandSql)

    return brand_id


def get_color_or_create(color):
    print "::::::Color :" + color + "::::::"
    sql = "select id from attributes where name ='color' and value = '%s'"
    cursor.execute(sql % color)
    data = cursor.fetchall()
    if len(data) > 0:
        attr_id = data[0][0]
    else:
        colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('color', color)
        attr_id = excute_insert_query(colorSql)
    return attr_id


def get_size_or_create(size):
    print "::::::Size :" + size + "::::::"
    sql = "select id from attributes where name ='size' and value = '%s'"
    cursor.execute(sql % size)
    data = cursor.fetchall()
    if len(data) > 0:
        attr_id = data[0][0]
    else:
        sizeSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('size', size)
        attr_id = excute_insert_query(sizeSql)
    return attr_id


def save_product_attribute(product_id, attr_id):
    sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
    excute_insert_query(sql)
    return True


def save_product_images(images, product_id):
    for image in images:
        try:
            print "::::::File :" + image + "::::::"
            img_name_db = create_file_name(image + time.ctime(int(time.time()))) + '.jpeg'
            img_name = 'product_images/' + img_name_db
            with open(img_name, "wb") as f:
                f.write(requests.get(image).content)
                sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
                excute_insert_query(sql)

        except:
            print (":::::::::::: File Error :::::::::::")


def save_product(ID, name, category, sub_category, price, product_price_original, brand_id, site_id, url):
    sql = "INSERT INTO products(identifier, title,category_id,sub_category_name, price,original_price, brand_id,site_id, details_url) VALUES " \
          "('%s', '%s', '%d', '%s', '%s','%s','%d','%d','%s')" % (
              ID, name, category, sub_category, price, product_price_original, brand_id, site_id, url)
    product_id = excute_insert_query(sql)

    return product_id


def create_file_name(image):
    return hashlib.md5(image).hexdigest()


def excute_insert_query(sql):
    insert_id = 0
    try:
        cursor.execute(sql)
        connection.commit()
        insert_id = cursor.lastrowid
    except Exception as e:
        connection.rollback()
        print e
        # break
    return insert_id

wd = webdriver.PhantomJS(phantomjs)

def get_soup(rel_url):
    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(rel_url)
            content = driver.page_source
            page = BeautifulSoup(content, 'html.parser')
    except:
        page = ""
        print("Connection refused by the server..")
    return page


def explore_top_menu():
    page = get_soup(base_url)
    mainnav = page.find(class_='container-desktop-nav')
    divs = mainnav.find(class_='flatheader').find_all(class_='category-title')
    for div in divs:
        anchor = div.find('a', class_='nav-item')
        navname =  anchor.text.strip().lower()
        if navname == 'men' or navname =='women':
            print ":::::::::::"+navname+"::::::::::::::::"
            subcontainers =  div.find_all(class_='container-titlesection')
            for index, item in enumerate(subcontainers):
                if index != 0:
                    conatiners = item.find_all(class_='subcontainer-item')
                    for nav in conatiners:
                        a = nav.find(class_='nav-item')
                        subcate =  a.text.strip()
                        rel =  base_url+a.get('href')
                        explore_list_page(rel,subcate,navname)


def explore_list_page(url, subcate, cate):
    page = get_soup(url)
    try:
        count = page.find(class_='product-count')
        count = count.text.strip()
        count = count[count.rfind('of'):].replace('of', '')
        count = int(math.ceil(int(count) / 60.0))
    except:
        print ":::::::::::Not A product page ::::::::::::::::"
        count = 0
    finally:
        pass
    if count > 0:
        print ":::::::::::"+subcate+"::::::::::::::::"
        for i in range(1, count + 1):
            print ":::::::::::url:"+url + "?page=" + str(i)+"::::::::::::::::"
            list_page = get_soup(url + "?page=" + str(i))
            time.sleep(3)
            products = list_page.find(class_='products').find_all(class_='product')
            for index,product in enumerate(products):
                identifier = product.get('data-id')
                rel_url = base_url + product.find(class_='name').find('a').get('href')
                grep(rel_url,subcate,cate,identifier)


def grep(url,subcate,cate,identifier):
    if not is_product_exists(identifier,site_id):
        page = get_soup(url)
        time.sleep(3)
        name = page.find('h1', attrs={"itemprop": "name"}).text.strip()
        print ":::::::::::" + name + "::::::::::::::::"
        price = get_price(page.find(class_='header2 _2VhMo').find('span', attrs={"itemprop": "price"}).text.strip())
        try:
            original_price = get_price(page.find(class_='_32a7b').text.strip())
        except:
            original_price = "0"
        print "::::::::::: Price " + price + " original " + original_price + "::::::::::::::::"
        product_id = save_product(identifier, name, product_type[cate], subcate, price, original_price, brand_id,
                                  site_id, url)
        colors = page.find(class_='colorSwatchGroup__Swatches _26Ukv').find_all('a')
        for anchor in colors:
            color = anchor.find(class_='colorSwatchNameName').text.strip()
            color_id = get_color_or_create(color)
            save_product_attribute(product_id, color_id)
        images = []
        try:
            slider = page.find(class_='flickity-slider').find_all('a')
            for anchor in slider:
                images.append(anchor.get('href'))
            save_product_images(images, product_id)
        except:
            slider = page.find(class_='_2D28O').find_all('a')
            for anchor in slider:
                images.append(anchor.get('href'))
            save_product_images(images, product_id)
        finally:
            pass



explore_top_menu()
