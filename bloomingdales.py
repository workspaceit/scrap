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
base_url = 'https://www.bloomingdales.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
site_id = 5
def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(id="paginationDdl")
        all_pages = pagination.find_all("option")
        first_item = all_pages[0].get('value')
        last_item = all_pages[-1].get('value')
        from_page = int(first_item)
        to_page = int(last_item)
        print ("Paginate from "+str(from_page)+" to "+str(to_page))
        go_to_pages(url,from_page,to_page,category,subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    splited_url = url.split("?")
    first_part = splited_url[0]
    last_part = splited_url[1]
    for page in range(from_page,to_page+1):
        regenerated_url = first_part+"/Pageindex/"+str(page)+"?"+last_part
        go_to_paginated_list_page(regenerated_url,category,subcategory)

def go_to_paginated_list_page(url,category,subcategory):

    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    products = product_list_page_soup.find_all(class_='productThumbnail')

    for product in products:
        id = product.get("id")
        product_url = product.find(class_='productThumbnailLink').get('href')
        product_brand = product.find(class_='brandName').find('a').string
        product_name = product.find(class_='prodName').find('a').string
        go_to_product_detail_page(product_url,product_name,id,product_brand,category,subcategory)

def go_to_product_detail_page(url,product_name,product_identifier,product_brand,category,subcategory):

    product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(product_dts_page.content, 'html.parser')


    json_obj= product_dts_soup.find(id='pdp_data')
    js = json_obj.string
    object = json.loads(js)
    print "JSON ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::"
    product_json= object["product"]

    product_price = None
    product_original_price=None
    if "salePrice" in product_json:
        product_price = product_json["salePrice"][0]
        product_original_price = product_json["price"][0]
    else:
        product_price = product_json["price"][0]
        product_original_price = 0

    product_price=str(product_price)
    product_original_price=str(product_original_price)

    sizes=[]
    sizeList = product_json['sizes']
    for size in sizeList:
        sizes.append(size)



    colors=[]
    colorList = product_json['colorFamily']
    for color in colorList:
        colors.append(color)

    print "IMAGES"

    allImages = []
    if "colorwayPrimaryImages" in product_json:
        imageList = product_json["colorwayPrimaryImages"]
        imgs=imageList.values()
        for img in imgs:
            splited = img.split(",")
            for splitd in splited:
                allImages.append(splitd)

    if "colorwayAdditionalImages" in product_json:
        imageList = product_json["colorwayAdditionalImages"]
        imgs = imageList.values()
        for img in imgs:
            splited = img.split(",")
            for splitd in splited:
                allImages.append(splitd)

    images=[]
    for image in allImages:
        image_src = "https://images.bloomingdales.com/is/image/BLM/products/"+image+"?wid=800&qlt=90,0&layer=comp&op_sharpen=0&resMode=sharp2&op_usm=0.7,1.0,0.5,0&fmt=jpeg"
        images.append(image_src)

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
    top = soup.find(id='mainNav')
    menus = top.find_all('a')
    selected_items = product_type.keys()
    for menu in menus:
        anchor_item = menu
        anchor= anchor_item.string.lower()
        if anchor in selected_items:
            partial_link = anchor_item.get('href')
            link=base_url+partial_link
            category_page = requests.get(link)
            category_page_soup = BeautifulSoup(category_page.content, 'html.parser')
            navs = category_page_soup.find(id='nav_category')
            categories = navs.find_all(class_='gn_left_nav_section')
            categories = categories[1:-2]
            for category in categories:
                cats = category.find_all(class_='gn_left_nav2_standard')
                for cat in cats:
                    sub_anchor=cat.find('a')
                    sub_partial_link = sub_anchor.get('href')
                    sub_category=sub_anchor.string
                    go_to_product_list_page(sub_partial_link,product_type[anchor],sub_category)
                    # break

            # break





start_scrapper()






