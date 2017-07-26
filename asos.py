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
base_url = 'http://www.asos.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
site_id = 12


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
brands = []
def get_brands(navs):
        uls = navs.find_all('ul', class_='items')
        lis = uls[-1].find_all('li')
        for li in lis:
            if li.text.strip() == "A To Z Of Brands":
                print li.find('a').get("href")
                link = li.find('a').get("href")
                brand_page = get_soup(link)
                listitems = brand_page.find('div', class_='brands-list').find_all(class_='brand-letter')
                for items in listitems:
                    lis = items.find_all('li')
                    for li in lis:
                        brands.append(li.string.strip())



def explore_top_menu():
    page = get_soup(base_url)
    time.sleep(3)
    if page != "":
        menus = page.find('ul', class_='floor-menus').find_all('li', class_='asyncNav')
        for item in menus:
            anchor = item.find('a')
            category = anchor.text.strip().lower()
            navs = item.find_all('dl', class_='section')
            get_brands(navs[1])
            print "brands:" + str(len(brands))
            uls = navs[0].find_all('ul', class_='items')
            for ul in uls:
                lis = ul.find_all('li')
                for li in lis:
                    try:
                        cssclass = li.find('a').get('class', [])
                    except:
                        cssclass = ""
                    rel_url = ""
                    if 'branddirectory' not in cssclass and cssclass != []:
                        try:
                            rel_url = li.find('a').get('href')
                        except:
                            print "Not A menu Item"
                        finally:
                            pass
                        if rel_url != "":
                            explore_list_page(rel_url, category)


def explore_list_page(url,cate):
    page = get_soup(url)
    time.sleep(3)
    if page != "":
        subcate = page.find(class_='creative').find('h1').text.strip()
        print "::::::::::::::::::::::" + subcate + "::::::::::::::::::::::::::"
        pagination = page.find('ul', class_='pager').find_all('li')
        count = int(pagination[len(pagination)-1].text.strip())
        for i in range(0, count):
            rel_url =  url+"&pge="+str(i)+"&pgesize=36"
            print "::::::::::::::::::::::"+rel_url+"::::::::::::::::::::::::::"
            list_page = get_soup(rel_url)
            time.sleep(3)
            try:
                prodlist = list_page.find(class_='product-list').find('ul').find_all('li', class_='product-container')
                for product in prodlist:
                    identifier = product.get("data-productid")
                    anchor = product.find('a').get('href')
                    grep(identifier, anchor, subcate, cate)
            except:
                print "::::::::::::::::::::::Error Occured::::::::::::::::::::::::::"
            finally:
                pass




def grep(identifier,url,subcate,cate):
    if not is_product_exists(identifier,site_id):
        page = get_soup(url)
        time.sleep(3)
        if page != "":
            productdetails = page.find('section', attrs={'id': 'core-product'})
            hero = productdetails.find(class_='product-hero')
            name = hero.find('h1').text.strip()
            print "::::::::::::::::::::::" + name + "::::::::::::::::::::::::::"
            brand_id = 0
            for brand in brands:
                res = name.startswith(brand.strip())
                if res:
                    brand_id = get_brand_or_create(brand)
                    break
            try:
                price = get_price(hero.find(class_='product-price').find(class_='current-price').text.strip())
                original_price = get_price(
                    hero.find(class_='product-price').find('span', attrs={'data-id': 'previous-price'}).text.strip())
            except:
                price = 0
                original_price = 0
            print ":::::::::::::::::::::: Price :" + price + " original: " + original_price + "::::::::::::::::::::::::::"
            product_id = save_product(identifier, name, product_type[cate], subcate, price, original_price, brand_id,
                                      site_id, url.replace("'", "\\'"))
            sizes = productdetails.find('select', attrs={'data-id': 'sizeSelect'}).find_all('option')
            if len(sizes) > 0:
                for size in sizes:
                    if size.text.strip() != "Please select":
                        s = size.string.strip().replace('- Not available', '')
                        size_id = get_size_or_create(s)
                        save_product_attribute(product_id, size_id)
            elif productdetails.find(class_='size-section').find('span', class_='product-size').text.strip() != "":
                s = productdetails.find(class_='size-section').find('span', class_='product-size').text.strip()
                size_id = get_size_or_create(s)
                save_product_attribute(product_id, size_id)
            else:
                print "::::::::::::::::::::::No Size for product ::::::::::::::::::::::::::"

            colors = productdetails.find('select', attrs={'data-id': 'colourSelect'}).find_all('option')
            if len(colors) > 0:
                for color in colors:
                    if color.text.strip() != "Please select" and color.text.strip() != "Please select from 1 colours":
                        c = color.string.strip().replace('- Not available', '')
                        color_id = get_color_or_create(c)
                        save_product_attribute(product_id, color_id)
            elif productdetails.find(class_='colour-section').find('span', class_='product-colour').text.strip() != "":
                c = productdetails.find(class_='colour-section').find('span', class_='product-colour').string.strip()
                color_id = get_color_or_create(c)
                save_product_attribute(product_id, color_id)
            else:
                print "::::::::::::::::::::::No Color for product ::::::::::::::::::::::::::"

            ul = productdetails.find(class_='window').find('ul').find_all('li')
            images = []
            for li in ul:
                src = li.find('img').get('src').replace('513', '1026')
                images.append(src)
            save_product_images(images, product_id)
