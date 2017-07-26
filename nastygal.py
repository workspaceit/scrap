import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import hashlib
import time
import math
import json
from StringIO import StringIO
import selenium.webdriver as webdriver
import contextlib
import re

phantomjs = 'phantomjs'
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'http://www.nastygal.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}


def create_file_name(image):
    return hashlib.md5(image).hexdigest()


def execute_insert_query(sql):
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


def explore_top_menu():
    page = BeautifulSoup(requests.get(base_url).content, 'html.parser')
    navs = page.find('ul', class_='menu-category').find_all('li', class_='level-1-tab')
    for nav in navs:
        url = nav.find('a').get('href').replace('/gb', '')
        explore_list_page(url)


def explore_list_page(url):
    page = BeautifulSoup(requests.get(base_url + url).content, 'html.parser')
    list_pages = page.find('ul', class_='pagination-list').find_all('li')
    last_count = int(list_pages[len(list_pages) - 2].text)
    for i in range(0, last_count):
        products = BeautifulSoup(requests.get(base_url + url + '?sz=80&start=' + str(i * 80)).content,
                                 'html.parser').find('ul', class_='search-result-items').find_all('li',
                                                                                                  class_='grid-tile')
        for product in products:
            identifier = product.find(class_='product-tile').get('id')
            url = product.find('a', class_='thumb-link').get('href')
            grep(url,identifier)

def grep(url,identifier):
    sql = "SELECT * FROM products WHERE identifier ='%s'"
    cursor.execute(sql % identifier)
    data = cursor.fetchall()
    print len(data)
    if len(data) == 0:
        try:
            with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
                driver.get(base_url+url)
                content = driver.page_source
                page = BeautifulSoup(content, 'html.parser')
                breadcrumbs = page.find('ol', class_='breadcrumb').find_all('li', class_='breadcrumb-item')
                sub_cate = breadcrumbs[len(breadcrumbs) - 2].find('a', class_='breadcrumb-element').text
                title = page.find('h1', class_='product-name').string.strip().replace("'","")
                price = page.find('span', class_='price-sales').string.strip().replace('$', '')
                original_price = '0'
                try:
                    original_price = page.find('span', class_='price-standard').string.strip().replace('$', '')
                except:
                    original_price = '0'
                sql = "INSERT INTO products(identifier, title,category_id,sub_category_name, price, brand_id,site_id, details_url,original_price) VALUES " \
                      "('%s', '%s', '%d', '%s', '%s','%d','%d','%s','%s')" % (
                          identifier, re.escape(title), 1,  re.escape(sub_cate), price, 0, 7,base_url+url, original_price)
                product_id = execute_insert_query(sql)
                print product_id

                colors = page.find('ul', class_='color').find_all('li', class_='selectable')
                for color in colors:
                    span = color.find('span').get('data-variation-values')
                    io = StringIO(span)
                    clr = json.load(io).get('attributeValue')
                    sql = "select id from attributes where name ='color' and value = '%s'"
                    cursor.execute(sql % clr)
                    data = cursor.fetchall()
                    if len(data) > 0:
                        attr_id = data[0][0]
                    else:
                        colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('color', clr)
                        attr_id = execute_insert_query(colorSql)
                    sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
                    execute_insert_query(sql)

                sizes = page.find('ul', class_='size').find_all('li', class_='selectable')
                for size in sizes:
                    span = size.find('span').get('data-variation-values')
                    io = StringIO(span)
                    siz =  json.load(io).get('attributeValue')
                    sql = "select id from attributes where name ='size' and value = '%s'"
                    cursor.execute(sql % siz)
                    data = cursor.fetchall()
                    if len(data) > 0:
                        attr_id = data[0][0]
                    else:
                        colorSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('size', siz)
                        attr_id = execute_insert_query(colorSql)
                    sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
                    execute_insert_query(sql)
                images = page.find('ul', class_='product-thumbnails-list').find_all('li', class_='thumb')
                for image in images:
                    img = image.find('a', class_='thumbnail-link').get('href')
                    print img
                    img_name_db = create_file_name(img + time.ctime(int(time.time()))) + '.jpeg'
                    img_name = 'product_images/' + img_name_db
                    print img_name
                    try:
                        with open(img_name, "wb") as f:
                            f.write(requests.get(img).content)
                            sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
                            execute_insert_query(sql)
                    except Exception as e:
                        print(e)

        except:
            print("Connection refused by the server..")
