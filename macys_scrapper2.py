import mysql.connector
import requests
import validators
from bs4 import BeautifulSoup
import re
import json
import hashlib
import time

connection = mysql.connector.connect(user='root', password='', host='localhost', database='ecom')
cursor = connection.cursor()
base_url = 'https://www.macys.com'
product_type = {
    'women': 1,
    'men': 2,
    'home': 3,
    'kids': 4
}
phantomjs = 'phantomjs'
site_id = 2
def go_to_product_list_page(url,category,subcategory):
    print("link:" + url)

    try:
        product_list_page = requests.get(url)
        product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
        pagination = product_list_page_soup.find(class_="pagination")
        first_item = pagination.find(class_='currentPage')
        all_pages = pagination.find_all('a')
        from_page = int(first_item.string)
        to_page = int(all_pages[-3].string)
        print ("Paginate from "+str(from_page)+" to "+str(to_page))
        go_to_pages(url,from_page,to_page,category,subcategory)

    except:
        print("Connection refused by the server..")
        pass

def go_to_pages(url,from_page, to_page,category,subcategory):
    splited_url = url.split("?")
    first_part = splited_url[0]
    last_part = splited_url[1]
    brand_url = base_url+"/shop/all-brands/?"+last_part
    brand_list_page = requests.get(brand_url)
    soup = BeautifulSoup(brand_list_page.content, 'html.parser')
    brands = soup.find_all(class_='brand-box')
    all_brands=[]
    for brand in brands:
        brand_list = brand.find_all('a')
        for brand_item in brand_list:
            if brand_item.string is not None:
                all_brands.append(brand_item.string)

    for page in range(from_page,to_page+1):
        regenerated_url = first_part+"/Pageindex/"+str(page)+"?"+last_part
        go_to_paginated_list_page(regenerated_url,category,subcategory,all_brands)

def go_to_paginated_list_page(url,category,subcategory,brands):
    print url
    brands.remove("Macy's")
    product_list_page = requests.get(url)
    product_list_page_soup = BeautifulSoup(product_list_page.content, 'html.parser')
    products = product_list_page_soup.find_all(class_='productThumbnail')

    for product in products:
        id = product.get("id")
        link = product.find(class_='productThumbnailLink').get('href')
        product_url = base_url+link
        product_name = product.find(class_="shortDescription").find('a').string
        product_name = product_name.strip()
        product_name = product_name.replace("'","")

        price = product.find(class_="priceSale").string
        price = price.split("$")[1]
        original_price = product.find(class_="first-range").string
        original_price = original_price.split("$")[1]

        if price == original_price:
            original_price = 0

        product_brand = None
        # print product_name
        for brand in brands:
            res = product_name.startswith(brand.strip())
            if res:
                product_brand = brand
                break

        # imageList=[]
        # images = product.find(class_='innerWrapper')
        # json_str= images.find('script').string
        # json_obj = json.loads(json_str)
        # if 'swatchColorList' in json_obj:
        #     image_list= json_obj['swatchColorList']
        #     for img in image_list:
        #         imageList.append(img.values()[0])



        print "Product :"+product_url
        print "brand :"+product_brand
        go_to_product_detail_page(product_url,product_name,id,product_brand,price,original_price,category,subcategory)


def go_to_product_detail_page(url,product_name,product_identifier,product_brand,product_price,product_price_original,category,subcategory):
    product_dts_page  = requests.get(url)
    product_dts_soup = BeautifulSoup(product_dts_page.content, 'html.parser')

    colors=[]
    colorList = product_dts_soup.find_all(class_='colorSwatch')
    for color in colorList:
        colors.append(color.get('alt'))

    sizes = []
    sizeList = product_dts_soup.find_all(class_='size')
    for size in sizeList:
        sizes.append(size.get('title'))


    images=[]
    all_images = product_dts_soup.find(class_='features-zoomer').find('noscript')
    imageList = all_images.find_all('img')
    for image in imageList:
        img=image.get('src').split("&")[0]+"&wid=404"
        images.append(img)

    save_product_to_db(url, product_name, product_identifier, product_brand, product_price, product_price_original,category, subcategory, colors, sizes, images)

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
    top = soup.find(id='mainNavigation')
    menus = top.find_all(class_='fob')
    selected_items = product_type.keys()
    for menu in menus:
        anchor_item = menu.find('a')
        anchor= anchor_item.string.lower()
        if anchor in selected_items:
            partial_link = anchor_item.get('href')
            link=base_url+partial_link
            category_page = requests.get(link)
            category_page_soup = BeautifulSoup(category_page.content, 'html.parser')
            first_ul = category_page_soup.find(id='firstNavSubCat')
            sub_anchors = first_ul.select('.nav_cat_item_bold ul li a')
            for sub_anchor in sub_anchors:
                sub_partial_link = sub_anchor.get('href')
                sub_category=sub_anchor.string
                go_to_product_list_page(sub_partial_link,product_type[anchor],sub_category)











