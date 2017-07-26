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
import dryscrape
connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.net-a-porter.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
site_id = 22
sess = dryscrape.Session()
def go_to_product_list_page(url,category,subcategory):
    # print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(class_="product-list-pagination")
        first_item = 1
        last_item = pagination.find(class_='pagination-links').get('data-lastpage')
        from_page = int(first_item)
        to_page = int(last_item)
        if to_page == 1:
            go_to_paginated_list_page(url, category, subcategory)
        else:
            print ("Paginate from " + str(from_page) + " to " + str(to_page))
            go_to_pages(url,from_page,to_page,category,subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    for page in range(from_page,to_page+1):
        regenerated_url = url+"?pn="+str(page)+"&npp=60&image_view=product&dScroll=0"
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):
    print "-----"
    print "LINk"
    print url
    print "------"
    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    product_container = product_list_page_soup.find(class_='products')
    products = product_container.find_all('li')
    for product in products:
        description = product.find(class_='description')
        anchor = description.find('a')
        parial_url =anchor.get('href')
        product_url= base_url+parial_url
        product_id = parial_url.split("/")
        id= product_id[4]
        product_name= anchor.get('title')
        product_brand = anchor.find(class_='designer').string
        # product_price_desc = description.find('span',class_='price')
        # product_price_text = product_price_desc.getText().strip()
        # prices =re.findall("\$(\d+.\d+)",product_price_text)
        #
        # print ">>>>>>>>>>>>>>>>>>"
        # print id
        # print product_url
        # print product_name
        # print product_brand
        # print prices
        # print "<<<<<<<<<<<<<<<<<<<<<"

        go_to_product_detail_page(product_url,product_name,id,product_brand,category,subcategory)

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,category,subcategory):


    sess.visit(url)
    response = sess.body()
    # product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(response, 'html.parser')

    product_full_price_container = product_dts_soup.find(class_='full-price')

    product_original_price=0
    if product_full_price_container:
        product_original_price = product_full_price_container.string

    product_price_container = product_dts_soup.find(class_='sale-price')
    product_price = 0
    if product_price_container:
        product_price = product_price_container.string

    size_container = product_dts_soup.find(id='select')
    sizes=[]
    if size_container:
        sizeList = size_container.find_all('option')
        if sizeList:
            for size in sizeList:
                value = size.get('data-size')
                if value:
                    sizes.append(value)

    images=[]
    image_container = product_dts_soup.find(class_='thumbnails')
    if image_container:
        imageList = image_container.find_all('img')
        if imageList:
            for image in imageList:
                img = image.get('src')
                img = img.replace("_xs","_pp")
                images.append(img)


    colors=[]
    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
    print url
    print colors
    print product_original_price
    print product_price
    print "<<<<<<<<<<<<<<<<<<<<<<<<<<<"
    save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_original_price,category, subcategory, colors, sizes, images)

def save_product_to_db(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory,colors,sizes,images):
    print("!!!!!!!!!!!!!!!!!!!!!!!!!SAVING INTO DATABASE !!!!!!!!!!!!!!!")

    if not is_product_exists(product_identifier,site_id):
       brand_id = get_brand_or_create(product_brand)
       product_id = save_product(product_identifier,product_name,category,subcategory,product_price,product_price_original,brand_id,site_id,url)

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
        if image.startswith("//"):
           image = "http:"+image


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
    try:

        # sess = dryscrape.Session()
        sess.visit(base_url)
        response = sess.body()
        product_dts_soup = BeautifulSoup(response, 'html.parser')
        top = product_dts_soup.find(class_='nav-links')
        navs = top.find('li',class_='nav-sale').find('a').get('href')
        sale_url = base_url+navs

        page = requests.get(sale_url)
        soup = BeautifulSoup(page.content,'html.parser')
        category_container = soup.find(id='sale-container')
        categories = category_container.find_all('li')
        for category in categories:
            class_name = category.get('class')
            if class_name[0] != 'all':
                sub_category = category.find('a').string
                partial_url = category.find('a').get('href')
                url = base_url+partial_url
                go_to_product_list_page(url,1,sub_category)

    except Exception as e:
        print e





start_scrapper()



