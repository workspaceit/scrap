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
base_url = 'https://www.shopbop.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
site_id = 24

def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(class_="pagination")
        first_item = 1
        last_item = pagination.find_all('span',class_='page-number')[-1].getText()
        from_page = int(first_item)
        to_page = int(last_item)
        print ("Paginate from " + str(from_page) + " to " + str(to_page))
        go_to_pages(url, from_page, to_page, category, subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    for page in range(from_page,to_page+1):
        page_index = (page-1)*100
        regenerated_url = url+"?baseIndex="+str(page_index)
        print regenerated_url
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):
    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    product_container = product_list_page_soup.find(id='product-container')
    products = product_container.find_all('li',class_='product')
    for product in products:
        id = product.get('data-productid')
        product_url = base_url+product.find('a').get('href')
        product_name = product.find(class_='title').getText()
        product_brand = product.find(class_='brand').getText()
        product_original_price = product.find(class_='retail-price').getText()
        product_sale_price = product.find(class_='sale-price-low').getText()
        if product_original_price == product_sale_price:
            product_original_price = 0
        go_to_product_detail_page(product_url,product_name,id,product_brand,category,subcategory,product_original_price, product_sale_price)

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,category,subcategory,product_original_price,product_price):

    product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(product_dts_page.content, 'html.parser')



    size_container = product_dts_soup.find(id='sizes')
    sizes=[]
    if size_container:
        sizeList = size_container.find_all('span')
        if sizeList:
            for size in sizeList:
                value = size.get('data-selectedsize')
                if value:
                    sizes.append(value)

    color_container = product_dts_soup.find(id='swatches')
    colors = []
    if color_container:
        colorList = color_container.find_all('img')
        if colorList:
            for color in colorList:
                value = color.get('alt')
                if value:
                    colors.append(value)

    images=[]
    image_container = product_dts_soup.find(class_='thumbnail-list')
    if image_container:
        imageList = image_container.find_all('li',class_='thumbnailListItem')
        imageList = imageList[:-1]
        if imageList:
            for image in imageList:
                img = image.find('img').get('src')
                img = img.replace("_QL90_UX37_.","")
                images.append(img)


    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>"
    print url
    print colors
    print images
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
        page = requests.get(base_url)
        content = page.content
        soup = BeautifulSoup(content,"html.parser")
        topmenu = soup.find(id='navList')
        menus= topmenu.find_all("li",class_='navCategory')
        for menu in menus:
            menu_item = menu.find('a')
            menu_url = menu_item.get('href')
            name = menu_item.get('data-cs-name')
            if name=='clothing' or name == 'shoes' or name=='bags' or name=='accessories':
                category_url = base_url+menu_url
                category =1
                category_page = requests.get(category_url)
                category_soup = BeautifulSoup(category_page.content,"html.parser")
                leftnavs = category_soup.find_all('li',class_='leftNavCategoryLi')
                leftnavs = leftnavs[1:]
                for lnav in leftnavs:
                    nav_item = lnav.find('a')
                    url = base_url+nav_item.get('href')
                    sub_category= nav_item.getText()
                    go_to_product_list_page(url,category,sub_category)

    except Exception as e:
        print e










