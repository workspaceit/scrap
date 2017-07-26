import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import re
import json
import hashlib
import time
from selenium import webdriver
import contextlib

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'http://www.menswearhouse.com/'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
subcategories = [
    {
        "name": "Suits",
        "url": "mens-suits"
    },
    {
        "name": "Blazers & Sport Coats",
        "url": "sport-coats"
    },
    {
        "name": "Dress Shirts",
        "url": "dress-shirts"
    },
    {
        "name": "Casual Shirts",
        "url": "mens-suits"
    },
    {
        "name": "Pants & Shorts",
        "url": "mens-pants"
    },
    {
        "name": "Jeans",
        "url": "mens-clothes/mens-jeans"
    },
    {
        "name": "Vests",
        "url": "mens-clothes/vests"
    },
    {
        "name": "Ties",
        "url": "mens-clothes/ties"
    },
    {
        "name": "Sweaters",
        "url": "mens-clothes/mens-sweaters"
    },
    {
        "name": "Tuxedos & Formalwear",
        "url": "mens-clothes/formalwear"
    },
    {
        "name": "Outerwear",
        "url": "mens-clothes/mens-outerwear"
    },
    {
        "name": "Boys",
        "url": "boys-clothes"
    },
    {
        "name": "Dress Shoes",
        "url": "mens-shoes/mens-dress-shoes"
    },
    {
        "name": "Casual Shoes",
        "url": "mens-shoes/mens-casual-shoes"
    },
    {
        "name": "Loafers & Slip-Ons",
        "url": "mens-shoes/mens-loafers"
    },
    {
        "name": "Boat Shoes",
        "url": "mens-shoes/boat-shoes"
    },
    {
        "name": "Oxfords",
        "url": "mens-shoes/mens-oxford-shoes"
    },
    {
        "name": "Sandals",
        "url": "mens-shoes/mens-sandals"
    },
    {
        "name": "Sneakers",
        "url": "mens-shoes/mens-sneakers"
    },
    {
        "name": "Tuxedo Formal Shoes",
        "url": "mens-shoes/mens-formal-shoes"
    },
    {
        "name": "Boots",
        "url": "mens-shoes/mens-boots"
    },
    {
        "name": "Slippers",
        "url": "mens-shoes/mens-slippers"
    },
    {
        "name": "Belts & Suspenders",
        "url": "mens-clothing-accessories/mens-belts"
    },
    {
        "name": "Clothing & Shoe Care",
        "url": "mens-clothing-accessories/shoe-care"
    },
    {
        "name": "Cologne & Skin Care",
        "url": "mens-clothing-accessories/cologne"
    },
    {
        "name": "Cufflinks",
        "url": "mens-clothing-accessories/cufflink-stud-sets"
    },
    {
        "name": "Watches",
        "url": "mens-clothing-accessories/watches"
    },
    {
        "name": "Lapel Pins",
        "url": "mens-clothing-accessories/lapel-pins"
    },
    {
        "name": "Pocket Squares",
        "url": "mens-clothing-accessories/pocket-squares"
    },
    {
        "name": "Scarves, Hats & Gloves",
        "url": "mens-clothing-accessories/scarves"
    },
    {
        "name": "Socks",
        "url": "mens-clothing-accessories/mens-socks"
    }, {
        "name": "Tie Bars & Tie Chains",
        "url": "mens-clothing-accessories/tie-clips"
    },
    {
        "name": "Underwear",
        "url": "mens-clothing-accessories/mens-underwear"
    },
    {
        "name": "Luggage, Bags & Umbrellas",
        "url": "mens-clothing-accessories/luggage"
    },

]


def go_to_product_list_page(url, category, subcategory):
    url = base_url+url


    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(url)
            content = driver.page_source
            soup = BeautifulSoup(content, 'html.parser')
            product_count_text = soup.find(class_='productTotalCountAboveFilter').string
            print ">>>>>>>>>>>>>>>>>>"

            print url
            product_count = int(product_count_text.strip())
            print "Product Count :"+str(product_count)
            no_of_scroll = (product_count/16)+1
            print "No of Scroll to be happened :"+str(no_of_scroll)

            for i in range(1, no_of_scroll+1):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                html_source = driver.page_source

            product_dts_soup = BeautifulSoup(html_source, 'html.parser')
            products = product_dts_soup.find_all(class_='new-arrival')
            for product in products:
                anchor = product.find('a')
                product_url = anchor.get('href')
                product_id = product_url.split("-")[-1]
                product_name = anchor.get('title')

                product_price_original=0
                product_price=0
                product_price_container = product.find(class_='prod-price')
                if product_price_container:
                   product_prices = product_price_container.find_all('input')
                   length = len(product_prices)
                   if length>1:
                       product_price_original=product_prices[0].get('value')
                       product_price=product_prices[1].get('value')
                       product_price = product_price[1:]
                       product_price_original = product_price_original[1:]

                   elif length ==1:
                       product_price_original = str(0)
                       product_price = product_prices[0].get('value')
                       product_price = product_price[1:]

                product_price = str(product_price)
                product_price_original = str(product_price_original)

                go_to_product_detail_page(product_url,product_name,product_id,0,category,subcategory,product_price,product_price_original)
            print "<<<<<<<<<<<<<<<<<<<"


    except Exception as e:
        print e


def go_to_pages(url, from_page, to_page, category, subcategory):
    splited_url = url.split("?")
    first_part = splited_url[0]
    last_part = splited_url[1]
    for page in range(from_page, to_page + 1):
        regenerated_url = first_part + "/Pageindex/" + str(page) + "?" + last_part
        go_to_paginated_list_page(regenerated_url, category, subcategory)


def go_to_paginated_list_page(url, category, subcategory):
    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    products = product_list_page_soup.find_all(class_='productThumbnail')

    for product in products:
        id = product.get("id")
        product_url = product.find(class_='productThumbnailLink').get('href')
        product_brand = product.find(class_='brandName').find('a').string
        product_name = product.find(class_='prodName').find('a').string
        go_to_product_detail_page(product_url, product_name, id, product_brand, category, subcategory)


def go_to_product_detail_page(url, product_name, product_identifier, product_brand, category, subcategory,product_price,product_price_original):
    try:
        with contextlib.closing(webdriver.PhantomJS(phantomjs)) as driver:
            driver.get(url)
            content = driver.page_source

            # product_dts_page = requests.get(url)
            product_dts_soup = BeautifulSoup(content, 'html.parser')

            print  url
            colors = []
            color_container = product_dts_soup.find_all(class_='color-swatches')
            if color_container:
                colorList = product_dts_soup.find_all('a',class_='js-swatch-item')
                for color in colorList:
                    colors.append(color.get('data-color-name'))

            sizes = []
            size_container = product_dts_soup.find_all(class_='sizes-wrap')
            if size_container:
                sizeList = product_dts_soup.find_all('li', class_='size-item')
                for size in sizeList:
                    sizes.append(size.get('data-size'))

            images = []
            image_container= product_dts_soup.find(class_='pdp-thumbs')

            if image_container:
               imageList = image_container.find_all('img')
               if imageList:
                   for image in imageList:
                       img = image.get('src')
                       img = img.replace("$cart$","$40MainPDP$")
                       images.append(img)

            if len(images) == 0:
                only_image = product_dts_soup.find(class_='pdp-main-image-container').find('img')
                image = only_image.get('src')
                images.append(image)

            save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_price_original,
                              category, subcategory, colors, sizes, images)



    except Exception as e:
        print e



def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    try:
        if not is_product_exists(product_identifier,14):
           if product_brand != 0:
               brand_id = get_brand_or_create(product_brand)
           else:
               brand_id = 0

           product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,14,url)

           for color in colors:
               color_id = get_color_or_create(color)
               save_product_attribute(product_id,color_id)

           for size in sizes:
               size_id = get_size_or_create(size)
               save_product_attribute(product_id, size_id)

           save_product_images(images,product_id)
        else:
            print("ALREADY SAVED IN DATABASE")

    except Exception as e:
        print e

def is_product_exists(product_id,site_id):
    sql = "SELECT * FROM products WHERE identifier ='{0}' and site_id={1}"
    sql = sql.format(product_id,site_id)
    cursor.execute(sql)
    data = cursor.fetchall()
    if len(data)==0:
        return False
    else:
        return True

def get_brand_or_create(brand):
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
    sql = "select id from attributes where name ='size' and value = '%s'"
    cursor.execute(sql % size)
    data = cursor.fetchall()
    if len(data) > 0:
        attr_id = data[0][0]
    else:
        sizeSql = "insert into attributes (name,value) VALUES ('%s','%s')" % ('size', size)
        attr_id = excute_insert_query(sizeSql)
    return attr_id

def save_product_attribute(product_id,attr_id):
    sql = "insert into products_attributes (product_id,attr_id) VALUES ('%d','%d')" % (product_id, attr_id)
    excute_insert_query(sql)
    return True

def save_product_images(images,product_id):
    print images
    for image in images:
        img_name_db = create_file_name(image + time.ctime(int(time.time()))) + '.jpeg'
        img_name = 'product_images/' + img_name_db
        with open(img_name, "wb") as f:
            f.write(requests.get(image).content)
            sql = "insert into product_image (path,product_id) VALUES ('%s','%d')" % (img_name, product_id)
            excute_insert_query(sql)

def save_product(ID,name,category,sub_category,price,product_price_original,brand_id,site_id,url):

    sql = "INSERT INTO products(identifier, title,category_id,sub_category_name, price,original_price, brand_id,site_id, details_url) VALUES " \
          "('%s', '%s', '%d', '%s', '%s','%s','%d','%d','%s')" % (
              ID, name, category, sub_category, price,product_price_original, brand_id, site_id, url)
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

def start_scrapper():

    for subcategory in subcategories:
        go_to_product_list_page(subcategory["url"],2,subcategory["name"])


start_scrapper()
