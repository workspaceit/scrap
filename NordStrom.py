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
base_url = 'http://shop.nordstrom.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
site_id = 21


def explore_top_menu():
    page = BeautifulSoup(requests.get(base_url).content, 'html.parser')
    navs = page.find('ul', attrs={'role': 'tablist'}).find_all('li')
    menus = navs[-1].find('div').find_all('a')
    for menu in menus:
        name = menu.string.strip().lower()
        if name == 'women' or name == 'men' or name == 'kids' or name == 'home':
            print ":::::: In The top Menu :" + name + ":::::::::::::::"
            url = menu.get('href')
            print base_url+url
            explore_category_page(base_url+url,name)


def explore_category_page(url,cate):
    page = BeautifulSoup(requests.get(url).content, 'html.parser')
    sub_categories = page.find('ul', class_='nav-list').find_all('li', class_='nav-item')
    print ":::::: In The Category :" + cate + ":::::::::::::::"
    for li in sub_categories:
        try:
            anchor = li.find('a')
            subcate = li.find('span').string.strip()
            rel_url = base_url+anchor.get('href')
            print rel_url
        except:
            rel_url =""
            print "Error"
        if rel_url != "":
            explore_list_page(rel_url, subcate, cate)


def explore_list_page(url,subcate,cate):
    print ":::::: In The subcategory :" + subcate + ":::::::::::::::"
    print url
    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(url)
            content = driver.page_source
            page = BeautifulSoup(content, 'html.parser')

    except:
        page = ""
        print("Connection refused by the server..")

    if (page != ""):
        pages = page.find('ul', class_='page-numbers').find_all('li', class_='page-number')
        count = int(pages[-1].find('span').text.strip())
        for i in range(1, count + 1):
            print ":::::: In The subcategory :" + subcate + "::page:"+str(i)+":::::::::::::::"
            uri = url + "&offset=1&top=72&page=" + str(i)
            print uri
            with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
                driver.get(uri)
                content = driver.page_source
                list_page = BeautifulSoup(content, 'html.parser')
                products = list_page.find_all('div', class_='npr-gallery-item')
                for product in products:
                    classes = product.get('class', [])
                    if not 'npr-inline-promo' in classes:
                        anchor = product.find('p', class_='product-title').find('a').get('href')
                        rel_url = base_url + anchor
                        grep(rel_url,subcate,cate)



def grep(url,subcate,cate):
    category = product_type[cate]
    last = url.rfind('/')
    identifier = url[last:]
    identifier = identifier[:identifier.rfind('?')].replace('/', '')
    if (not is_product_exists(identifier, site_id)):
        try:
            with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
                driver.get(url)
                content = driver.page_source
                page = BeautifulSoup(content, 'html.parser')

        except:
            page = ""
            print("Connection refused by the server..")

        if page != "":
            print ":::::: In The Product ::::::::::::::::"
            productdetails = page.find('div', class_='product-details')

            try:
                brand = productdetails.find('section', class_='brand-title').find('h2').find('a').find(
                    'span').text.strip()
                brand_id = get_brand_or_create(brand)
            except:
                brand_id = 0

            title = productdetails.find('section', class_='np-product-title').find('h1').text.strip()
            print title
            price = productdetails.find(class_='current-price').string.strip().replace('$', '')
            price = get_price(price)
            try:
                original_price = productdetails.find(class_='original-price').string.strip().replace('$', '')
                original_price = get_price(original_price)
            except:
                original_price = 0
            print original_price
            product_id = save_product(identifier, title, category, subcate, price, original_price, brand_id, site_id,
                                      url)
            try:
                sizes = productdetails.find(class_='size-filter').find(class_='drop-down-options').find_all(
                    class_='drop-down-option')
                for div in sizes:
                    size = div.find(class_='option-main-text').text.strip()
                    size_id = get_size_or_create(size)
                    save_product_attribute(product_id, size_id)
            except:
                print "No size"
            try:
                colors = productdetails.find(class_='np-circular-swatches').find('ul').find_all('li')
                for li in colors:
                    color = li.find('img').get('alt').strip().replace('swatch image', '').replace('selected', '')
                    color_id = get_color_or_create(color)
                    save_product_attribute(product_id, color_id)
            except:
              color = productdetails.find(class_='color-filter').find('a',class_='np-circular-swatch').find('img').get('alt').strip().replace('swatch image', '').replace('selected', '')
              color_id = get_color_or_create(color)
              save_product_attribute(product_id, color_id)

            lis = page.find(class_='thumbnails').find('ul').find_all('li')
            images = []
            for li in lis:
                image = li.find('img').get('src').replace('w=60&h=90', 'w=704&h=1080')
                images.append(image)
            save_product_images(images, product_id)


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
        print "::::::File :" + image + "::::::"
        img_name_db = create_file_name(image + time.ctime(int(time.time()))) + '.jpeg'
        img_name = 'product_images/' + img_name_db
        with open(img_name, "wb") as f:
            f.write(requests.get(image).content)
            sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
            excute_insert_query(sql)


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

