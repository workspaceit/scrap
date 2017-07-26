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
base_url = 'https://www.ae.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
site_id = 13
brand_id = 358


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


def explore_top_menu():
    page = get_soup(base_url)
    time.sleep(3)
    nav = page.find('nav', class_='desktop').find_all(class_='top-link-container')
    for item in nav:
        itemname = item.find('span', class_='top-link-facade-container').find(
            class_='top-link-facade').text.strip().lower()
        if itemname == 'women' or itemname == 'men':
            print "::::::::::::::::::::::::"+itemname+"::::::::::::::::::::::::::::"
            flyouts = item.find(class_='flyout-container').find_all(class_='column')
            count = len(flyouts)
            for i in range(1, count - 1):
                print flyouts[i].find(class_='header').text.strip()
                anchors = flyouts[i].find_all('a', class_='column-link')
                for index, anchor in enumerate(anchors):
                    if index != 0 and i != (count - 1):
                        subcate = anchor.text.strip()
                        explore_list_page(base_url + anchor.get('href'),subcate,itemname)


def explore_list_page(url,subcate,cate):
    page = get_soup(url)
    time.sleep(3)
    if page != "":
        product_list = ""
        try:
            product_list = page.find(class_="product-list")
            print url
        except:
            print ":::::::::::::::::::::::: Not A List::::::::::::::::::::::::::::"

        if product_list != "":
            print "::::::::::::::::::::::::" + subcate + "::::::::::::::::::::::::::::"
            products = product_list.find_all(class_='product-tile')
            print len(products)
            for product in products:
                identifier = product.get('id')
                anchor = product.find('a')
                rel_url = base_url+anchor.get('href')
                grep(rel_url,identifier,subcate,cate)


def grep(url,identifier,subcate,category):
    identifier = identifier.replace("_", '')
    if not is_product_exists(identifier, site_id):
        page = get_soup(url)
        time.sleep(3)
        if page != "":
            product = page.find(class_='pdp-cap')
            name = product.find('h1', class_='psp-product-name').text.strip()
            print "::::::::::::::::::::" + name + ":::::::::::::::::::::"

            try:
                price = product.find(attrs={'id': 'psp-product-saleprice'}).text.strip()
                original_price = product.find(attrs={'id': 'psp-regular-price'}).text.strip()
            except:
                price = product.find(attrs={'id': 'psp-regular-price'}).text.strip()
                original_price = "0"
            print ":::::::::::::::::::: Price :" + price + " Original :" + original_price + ":::::::::::::::::::::"
            product_id = save_product(identifier, name, product_type[category], subcate, price, original_price,
                                      brand_id, site_id, url)

            colors = product.find(class_='psp-swatches-color').find_all(class_='psp-swatch-container')
            for swatch in colors:
                color = swatch.find('img').get('alt')
                color_id = get_color_or_create(color)
                save_product_attribute(product_id, color_id)
            sizes = product.find('ul', attrs={'id': 'psp-sizedropdown-menu'}).find_all('li')
            for li in sizes:
                size = li.text.strip()
                size_id = get_size_or_create(size.replace('- Out Of Stock',''))
                save_product_attribute(product_id, size_id)

            images = []
            imglist = product.find(attrs={'id': 'product-carousel'}).find(class_='carousel-inner').find_all(
                class_='item-img')
            for img in imglist:
                src = "https:" + img.get('data-image') + "?$PDP_78_Main$"
                images.append(src)
            save_product_images(images, product_id)

