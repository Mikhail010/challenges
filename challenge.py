# -*- coding: utf-8 -*-
import scrapy
import urllib.parse as urlparse
from urllib.parse import parse_qs
import re

class ChallengeSpider(scrapy.Spider):
    name = 'challenge'

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1
    }

    headers = {
        'authority': 'www.mtsosfilings.gov',
        'x-catalyst-secured': 'true',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'accept': 'text/html, */*; q=0.01',
        'x-security-token': 'null',
        'x-requested-with': 'XMLHttpRequest',
        'x-catalyst-async': 'true',
        'origin': 'https://www.mtsosfilings.gov',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://www.mtsosfilings.gov/',
        'accept-language': 'es-US,es;q=0.9,en-US;q=0.8,en;q=0.7,es-419;q=0.6',
    }

    data = {
        'QueryString': 'test',
        '_CBASYNCUPDATE_': 'true',
        '_CBHTMLFRAGNODEID_': 'W480',
        '_CBHTMLFRAGID_': '1589608374094',
        '_CBHTMLFRAG_': 'true',
        '_CBNODE_': 'W500',
        '_VIKEY_': '780090a9x17b8x472fx94b2xff279f80867d',
        '_CBNAME_': 'buttonPush'
    }
    # not used, but this is how I defined the values
    # paginate_data = {
    #     '_CBHTMLFRAGID_': 'increments by one',
    #     '_CBNODE_': '.registerItemSearch-results ID',
    #     '_CBNAME_': 'selectPage',
    #     '_CBVALUE_': 'change according to page'
    # }
    page_counter = 1

    def get_detail_form_data(self, cb_node):
        detail_form = dict(self.data)
        del detail_form['_CBASYNCUPDATE_']
        del detail_form['_CBHTMLFRAGNODEID_']
        del detail_form['_CBHTMLFRAGID_']
        del detail_form['_CBHTMLFRAG_']
        detail_form['_CBNODE_'] = cb_node
        detail_form['_CBNAME_'] = 'invokeMenuCb'
        detail_form['_CBVALUE_'] = ''
        return detail_form

    def start_requests(self):
        yield scrapy.Request(url='https://www.mtsosfilings.gov/', headers=self.headers,callback=self.form_page)

    def form_page(self, response: scrapy.http.Response):
        print(response.headers)
        yield scrapy.Request(url='https://www.mtsosfilings.gov/mtsos-master/relay.html?url=https%3A%2F%2Fwww.mtsosfilings.gov%2Fmtsos-master%2Fservice%2Fcreate.html%3FtargetAppCode%3Dmtsos-master%26targetRegisterAppCode%26service%3DregisterItemSearch&target=mtsos-master',
                                      headers=self.headers, callback=self.get_businesses)

    def get_businesses(self, response: scrapy.http.Response):
        print(response.css('h1 span span::text').get())
        parsed = urlparse.urlparse(response.url)
        self.token = parse_qs(parsed.query)['id'][0]
        script = response.xpath('//script[contains(., "viewInstanceKey:")]/text()').get()
        script2 = response.xpath('//script[contains(., "containerNodeId:")]/text()').get()

        searchOperator = response.css('.registerItemSearch-tabs-criteriaAndButtons-criteria-itemNameSearchOperatorBox-itemNameSearchOperatorSelector::attr(id)').get()
        advance = response.css('.Attribute-Advanced::attr(id)').get()
        vi_pattern = r"viewInstanceKey:('[A-Za-z0-9_\./\\-]*')"
        vi_match = re.search(vi_pattern, script)
        vikey = vi_match.group().split(':')[1].strip("'")

        guid_pattern = r'guid:([0-9]*)'
        guid_match = re.search(guid_pattern,script)
        guid = guid_match.group().split(':')[1]

        frag_node_pattern = "containerNodeId:'([A-Za-z0-9]*)'"
        frag_match = re.search(frag_node_pattern, script2)
        frag_node = frag_match.group(1)

        node = response.css('.appSearchButton::attr(id)').get()[4:]

        self.data[f'{searchOperator}-ItemNameSearchOperator'] = 'StartsWith'
        self.data[f'{advance}-Advanced'] = 'N'
        self.data['_VIKEY_'] = vikey
        self.data['_CBHTMLFRAGID_'] = str(guid)
        self.data['_CBHTMLFRAGNODEID_'] = str(frag_node)
        self.data['_CBNODE_'] = node
        yield scrapy.http.FormRequest(url=f'https://www.mtsosfilings.gov/mtsos-master/viewInstance/update.html?id={self.token}',
                                      formdata=self.data, headers=self.headers, callback=self.pagination)

    def pagination(self, response: scrapy.http.Response):
        containers = response.css('.appRepeaterContent .appRecord')
        for container in containers:
            # print(container.css('.appReceiveFocus').get)
            record_id = container.css('a::attr(id)').get()[4:]
            form_data = self.get_detail_form_data(record_id)
            print(container.css('.appReceiveFocus::text').get())
            yield scrapy.http.FormRequest(url=f'https://www.mtsosfilings.gov/mtsos-master/viewInstance/update.html?id={self.token}',
                                      formdata=form_data, callback=self.parse)

        # has_pagination = response.css('.appNextEnabled').get()
        # if has_pagination:
        #     self.page_counter += 1
        #     f_id = int(self.data['_CBHTMLFRAGID_'])
        #     f_id += 1
        #     self.data['_CBHTMLFRAGID_'] = str(f_id)
        #     self.data['_CBNAME_'] = 'selectPage'
        #     node = response.css('.registerItemSearch-results::attr(id)').get()[4:]
        #     self.data['_CBNODE_'] = node
        #     self.data['_CBVALUE_'] = str(self.page_counter)
        #     yield scrapy.http.FormRequest(
        #         url=f'https://www.mtsosfilings.gov/mtsos-master/viewInstance/update.html?id={self.token}',
        #         formdata=self.data, headers=self.headers, callback=self.pagination)

    def parse(self, response: scrapy.http.Response):
        status = response.xpath("(//div[contains(@class, 'BusinessStatus')]/div[2]/text())[1]").get()
        known_in_montana_name = response.xpath("(//div[contains(@class, 'ForeignKnownNameYn')]/div[2]/text())[1]").get()
        inactive_date = response.xpath("(//div[contains(@class, 'DeregistrationDate')]/div[2]/text())[1]").get()
        registration_date = response.xpath("//div[contains(@class, 'Attribute-RegistrationDate')]/div[2]/text()").get()
        expiration_date = response.xpath("//div[contains(@class, 'RenewalExpirationDate')]/div[2]/text()").get()
        description = response.xpath("//div[contains(@class, 'Attribute-BusinessDescription ')]/div[2]/text()").get()
        yield {
            'status': status,
            'known in montana name': known_in_montana_name,
            'inactive date': inactive_date,
            'registration date': registration_date,
            'expiration date': expiration_date,
            'description': description
        }
        # description = response.css('.Attribute-BusinessDescription .appAttrValue::text').get()
        # yield {
        #     'description': description
        # }
