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
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom1')
cursor = connection.cursor()
base_url = 'http://www.topshop.com'
product_type = {
    'women': 1,
    # 'men': 2,
    # 'home': 3,
    # 'kids': 4
}
site_id = 32


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
        finally:
            pass


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


driver = webdriver.Firefox(executable_path='/usr/local/bin/geckodriver')
# driver = webdriver.Chrome(executable_path = '/Users/wsit/Public/chromedriver')
driver.implicitly_wait(30)
verificationErrors = []
accept_next_alert = True
brands = []


def get_all_brands(nav):
    go = ""
    for item in nav:
        subnavs = item.find(class_='dropdown')
        if subnavs is not None:
            navname = item.find('a').text.strip().lower()
            if navname == 'brands':
                items = item.find('ul', class_='column_1').find_all('li')
                go = items[-1].find('a').get('href')
                print go
    if go != "":
        page = get_soup(go)
        navs = page.find_all(class_='columns')
        for div in  navs:
            anchors =  div.find_all('a')
            for anchor in anchors:
                brands.append(anchor.text)



def explore_top_menu():
    page = get_soup(base_url)
    nav = page.find('ul', class_='menu_nav_hor').find_all('li')
    get_all_brands(nav)
    print "brands :" + str(len(brands))
    for item in nav:
        subnavs = item.find(class_='dropdown')
        if subnavs is not None:
            navname = item.find('a').text.strip().lower()

            if navname == 'clothing' or navname == 'shoes' or navname == 'bags & accessories' or navname == 'beauty':
                print (":::::::::::::::::::::::::::::::::::::::In nav : " + navname + "::::::::::::::::::::::::::::::::::::::::::::::")
                items = subnavs.find_all('ul')
                for ul in items:
                    menus = ul.find_all('li')
                    for li in menus:
                        anchor = li.find('a')
                        rel_url =  anchor.get('href')
                        print rel_url
                        explore_list_page(rel_url)


def explore_list_page(url):
    page = get_soup(url)
    count = int(page.find('span', class_='count').text.strip())
    count = int(math.ceil(count / 15.0))
    subcate = re.escape(page.find('div',attrs={'id':'mainContent'}).find('h1').text.strip())
    print "::::::::::::::::::::::::::"+subcate+":::::::::::::::::::::::::::::::::::::::::::::"
    driver.get(url)
    for i in range(1, count):
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print "Scrolling :" + str(i)
        content = driver.page_source.encode('utf-8')
        list_page = BeautifulSoup(content, 'html.parser')
        products = list_page.find_all('div', class_='product')
        print len(products)
        for product in products:
            classes = product.get('class', [])
            if 'content' not in classes:
                anchor = product.find('a', class_='product_action')
                link = product.find('a', class_='product_name')
                rel_url =  base_url+link.get('href')
                grep(rel_url,subcate)


def grep(url,subcate):
    last = url.rfind('/')
    identifier = url[last:]
    identifier = identifier[:identifier.rfind('?')].replace('/', '')
    identifier = identifier[identifier.rfind('-'):].replace('-', '')
    if not is_product_exists(identifier, site_id):
        page = get_soup(url)
        productdetails = page.find('div', class_='product_detail')
        name = productdetails.find(class_='product_details').find('h1').text
        print "::::::::::::::::::::::: Product :"+name +"::::::::::::::::::::::"
        brand_id = 0
        # print product_name
        for brand in brands:
            res = name.startswith(brand.strip())
            if res:
                brand_id = get_brand_or_create(brand)
                break
        print ":::::::::::::::::: brand :"+ str(brand_id)+"::::::::::::::::::::::"
        try:
            price = productdetails.find('span', class_='product_price').text.strip()
            price = get_price(price)
            original_price = 0
        except:
            prices = productdetails.find(class_='product_prices')
            price = get_price(prices.find('span', class_='now_price').text.strip())
            original_price = get_price(prices.find('span', class_='was_price').text.strip())
        print ":::::::::::::::::: Price :"+ price + "original :" + str(original_price)+"::::::::::::::::::::::"

        product_id = save_product(identifier,re.escape(name),product_type['women'],subcate,price,original_price,brand_id,site_id,url)
        try:
            sizes = productdetails.find('select', class_='product_size').find_all('option')
            for opt in sizes:
                size =   opt.get('value').strip()
                print size
                size_id = get_size_or_create(size)
                save_product_attribute(product_id,size_id)
        except:
            sizes = productdetails.find('div', class_='product_size_buttons').find_all('label')
            for item in sizes:
                size =  item.text.strip()
                size_id = get_size_or_create(size)
                save_product_attribute(product_id, size_id)

        img_list = page.find('ul',class_='product_hero__wrapper').find_all('li')
        images = []
        for item in img_list:
            try:
               src = item.find('a').get('href')
               images.append(src)
            except:
                print "File exception"
            finally:
                pass
        save_product_images(images, product_id)


explore_top_menu()