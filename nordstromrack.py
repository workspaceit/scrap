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
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom1')
cursor = connection.cursor()
base_url = 'https://www.nordstromrack.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
site_id = 31
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
    link = requests.get(base_url)
    page = BeautifulSoup(link.content, 'html.parser')
    navs = page.find(class_='site-header__primary-nav').find('ul',class_='primary-nav').find_all('li',class_='primary-nav__item')
    submenus = []
    submenuheads = []
    for item in navs:
        name = item.find(class_='primary-nav__link').find('span').string.strip().lower()
        if name == 'women' or name == 'men' or name == 'kids' or name == 'home':
            uls = item.find_all('ul')
            for ul in uls:
                lis = ul.find_all('li')
                for li in lis:
                    classes = li.get('class',[])
                    if 'sub-nav__item--heading' in classes:
                        anchor = li.find('a')
                        url = base_url + anchor.get('href')
                        print "::::::::::: Top Nav "+anchor.text+"::::::::::::::::"
                        explore_list_page(url, name)
                        submenuheads.append(li)
                    else:
                        submenus.append(li)


def explore_list_page(url,cate):
    page = BeautifulSoup(requests.get(url).content, 'html.parser')
    paginations = page.find('ul',class_='pagination').find_all('li')
    total =  int(paginations[len(paginations)-2].string.strip())
    for i in range(1,total+1):
        rel_url = url+"?page="+ str(i)
        print "::::::::::: Url " + rel_url + "::::::::::::::::"
        list_page = get_soup(rel_url)
        if list_page != "":
            products = list_page.find_all('div',class_='product-grid__row')
            for product in products:
                p_url = base_url+product.find('a',class_='product-grid-item').get('href')
                grep(p_url,cate)


def grep(url,cate):
    identifier = url.replace('https://www.nordstromrack.com/shop/product/','')
    identifier =  identifier[:identifier.rfind('/')]
    if not is_product_exists(identifier,site_id):
        page = get_soup(url)
        if page != "":
            category = product_type[cate]
            bradcumbs = page.find('ul', class_='category-breadcrumbs').find_all('li')
            last = bradcumbs[-1]
            subcate = last.find('span', class_='category-breadcrumbs__label').text.strip()
            productdetails = page.find('div', class_='product-page__details')
            try:
                brand = productdetails.find('a', class_='product-details__brand').text.strip()
                brand_id = get_brand_or_create(brand)
            except:
                brand_id = 0

            title = re.escape(productdetails.find('span',class_='product-details__title-name').text.strip())
            price = get_price(productdetails.find('span', class_='product-details__sale-price').text.strip())
            try:
                original_price = get_price(productdetails.find('span' , class_='product-details__retail-price').find('del').text.strip())
            except:
                 original_price = 0

            print original_price
            product_id = save_product(identifier,title,category,subcate,price,original_price,brand_id,site_id,url)
            try:
                sizes = productdetails.find('fieldset' , class_='sku-option--size').find_all('label',class_='sku-item')
                for label in  sizes:
                    size = label.find(class_='sku-item__radio').get('value')
                    size_id = get_size_or_create(size)
                    save_product_attribute(product_id,size_id)
            except:
                print(":::::::::::::: No Size :::::::::::::::::")

            try:
                colors = productdetails.find('fieldset' , class_='sku-option--color').find_all('label',class_='sku-item')
                for label in colors:
                    color =  label.find(class_='sku-item__radio').get('value')
                    color_id = get_size_or_create(color)
                    save_product_attribute(product_id, color_id)
            except:
                print":::::::::::::: No Color ::::::::::::::::::"

            images = page.find(class_='product-thumbnail').find_all(class_='product-thumbnail__button')
            imgs = []
            for btn in images:
                src =  btn.find('img').get('src')
                src = src.replace('71x105', '868x1300').replace('medium', 'large')
                imgs.append(src)
            save_product_images(imgs,product_id)

explore_top_menu()