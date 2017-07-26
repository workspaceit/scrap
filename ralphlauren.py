import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import re
import json
import hashlib
import time
import selenium.webdriver as webdriver
import contextlib

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'http://www.ralphlauren.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    # 'kids': 4
}
phantomjs = 'phantomjs'

def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(class_="pagination")
        first_item = 1
        last_item = pagination.find(class_='total-pages').string
        from_page = int(first_item)
        to_page = int(last_item)
        print ("Paginate from "+str(from_page)+" to "+str(to_page))
        go_to_pages(url,from_page,to_page,category,subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    for page in range(from_page,to_page+1):
        regenerated_url = url+"&pg="+str(page)
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):

    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    products = product_list_page_soup.find_all(class_='product')

    for product in products:
        id = product.get("id")
        product_id = id.split("-")[1]
        url = product.find(class_='photo').get('href')
        product_url=base_url+url
        images=[]
        image = product.find(class_='photo').find('img').get('src')
        image= image.replace("_t240","_dt")
        images.append(image)
        image2=image.replace("_lifestyle","_alternate1")
        images.append(image2)
        go_to_product_detail_page(product_url,product_id,category,subcategory,images)

def go_to_product_detail_page(url,product_identifier,category,subcategory,images):


    product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(product_dts_page.content, 'html.parser')

    product_name = product_dts_soup.find(class_='prod-title').string
    product_brand = product_dts_soup.find(class_='prod-brand-logo').find('img').get('alt')


    price_container = product_dts_soup.find(class_='prod-price')
    sale_price = price_container.find(class_='sale-price')
    if sale_price :
        product_price = sale_price.find('span').string
        product_original_price = price_container.find(class_='reg-price').string
        product_price = product_price.split("$")[1]
        product_original_price = product_original_price.split("$")[1]
    else:
        product_price = price_container.find(class_='reg-price').string
        product_original_price = 0
        product_price = product_price.split("$")[1]
        product_original_price = str(product_original_price)

    print url
    print "sale price :" + product_price
    print "original price :" +product_original_price

    size_container = product_dts_soup.find(class_='size-swatches')
    all_sizes = size_container.find_all('li')
    sizes=[]
    for size in all_sizes:
        sizes.append(size.string)

    color_container = product_dts_soup.find(id='color-swatches')
    all_colors = color_container.find_all('li')
    colors = []
    for color in all_colors:
        colors.append(color.get('title'))

    save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_original_price,category, subcategory, colors, sizes, images)

def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    if not is_product_exists(product_identifier,16):
       brand_id = get_brand_or_create(product_brand)
       product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,16,url)

       for color in colors:
           color_id = get_color_or_create(color)
           save_product_attribute(product_id,color_id)

       for size in sizes:
           size_id = get_size_or_create(size)
           save_product_attribute(product_id, size_id)

       save_product_images(images,product_id)
    else:
        print("ALREADY SAVED IN DATABASE")

def is_product_exists(product_id,site_id):
    sql = "SELECT * FROM products WHERE identifier ={0} and site_id={1}"
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
    page = requests.get(base_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    navs = soup.find_all(class_='navitem')
    selected_items = product_type.keys()
    for nav in navs:
        anchor= nav.get('rel')
        if anchor in selected_items:
            partial_link = nav.find('a').get('href')
            link=base_url+partial_link
            category_page = requests.get(link)
            category_page_soup = BeautifulSoup(category_page.content, 'html.parser')
            categories = category_page_soup.find_all(class_='nav-items')
            categories = categories[:-2]
            for category in categories:
                cats = category.find_all('a')
                for cat in cats:
                    sub_anchor=cat
                    sub_partial_link = sub_anchor.get('href')
                    sub_category=sub_anchor.string
                    list_page_link = base_url+sub_partial_link
                    go_to_product_list_page(list_page_link,product_type[anchor],sub_category)





start_scrapper()






