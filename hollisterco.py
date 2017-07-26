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
base_url = 'https://www.hollisterco.com/shop/wd'
product_type = {
    'girls': 1,
    'guys': 2,
    'home': 3,
    'kids': 4
}
site_id = 22
brand_id = 425


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

        except Exception, e:
            print (":::::::::::: File Error" + str(e) + " :::::::::::")


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
    topnav = page.find('ul', class_='rs-nav__top-cats').find_all(class_='rs-nav__cat')
    for nav in topnav:
        navname = nav.find(class_='rs-nav__cat-label').text.strip().lower()
        if navname == "guys" or navname == "girls":
            ul = nav.find('ul', class_='rs-nav__accordion-items--secondary').find_all('li')
            for li in ul:
                litext = li.text.strip()
                if litext != "New Arrivals" and litext != "View All":
                    try:
                        anchor = li.find('a')
                    except:
                        anchor = ""
                    finally:
                        pass
                    if anchor != "" and anchor is not None and anchor.text.strip() != "New Arrivals":
                        subcate = anchor.text.strip()
                        rel_url = base_url.replace('/shop/wd', '') + anchor.get('href')
                        try:
                            explore_list_page(rel_url,subcate,navname)
                        except Exception, e:
                            print ('error' + str(e))
                        finally:
                            pass


def explore_list_page(url, subcate, cate):
    print url
    listPage = get_soup(url)
    print ":::::::::::::::::::::" + subcate + ":::::::::::::::::::"
    if listPage != "":
        try:
            lis = listPage.find('ul', class_='solr-pagination').find_all('li', class_='page-link-wrapper')
            print len(lis)
            last = int(lis[len(lis) - 1].text.strip())
            for i in range(0, last):
                pageurl = url + "?search-field=&sort=bestmatch&start=" + str(i * 90) + "&rows=90&filtered=true"
                print ":::::::::::::::::::::" + pageurl + ":::::::::::::::::::"
                page = get_soup(pageurl)
                time.sleep(3)
                products = page.find_all(class_='rs-product-card')
                list_products(products, cate, subcate)

        except:
            products = listPage.find_all(class_='rs-product-card')
            list_products(products, cate, subcate)
        finally:
            pass


def list_products(products, cate, subcate):
    for product in products:
        identifier = product.find(class_='grid-product').get('data-productid')
        link = base_url.replace('/shop/wd', '') + product.find('a', class_='grid-product__image-link').get('href')
        try:
            grep(link, identifier, subcate, cate)
        except:
            print ":::::::::::::::::::::Product error:::::::::::::::::::"
        finally:
            pass


def grep(url, identifier, subcate, cate):
    if not is_product_exists(identifier, site_id):
        page = get_soup(url)
        if page != "":
            name = page.find(class_='product-page-info__title').find('h1', class_='product-page-title').text.strip()
            print ":::::::::::::::::::::" + url + ":::::::::::::::::::"
            print ":::::::::::::::::::::" + name + ":::::::::::::::::::"
            try:
                price = get_price(page.find(class_='product-price-v2__price--offer').text.strip())
                original_price = get_price(page.find(class_='product-price-v2__price--sale').text.strip())
            except:
                price = get_price(page.find(class_='product-price-v2__price').text.strip())
                original_price = "0"
            print ":::::::::::::::::::::" + "Price " + price + " original " + original_price + ":::::::::::::::::::"
            product_id = save_product(identifier, name, product_type[cate], subcate, price, original_price, brand_id,
                                      site_id, url)
            colors = page.find('ul', class_='product-swatches').find_all(class_='product-attrs__attr')
            if len(colors) > 1:
                for color in colors:
                    name = color.get('aria-label')
                    color_id = get_color_or_create(name)
                    save_product_attribute(product_id, color_id)
            else:
                color = page.find('ul', class_='product-swatches').find('li').find('span').text.strip()
                color_id = get_color_or_create(color)
                save_product_attribute(product_id, color_id)
            sizes = page.find('ul', class_='product-sizes').find_all('li')
            for li in sizes:
                size = li.text.strip()
                size_id = get_size_or_create(size)
                save_product_attribute(product_id, size_id)
            images = []
            imgs = page.find('ul', class_='product-main-images').find_all('li')
            for li in imgs:
                src = "https:" + li.find('img').get('src')
                images.append(src)
            save_product_images(images, product_id)
