import requests
from urllib.parse import urlencode

class Client:
    def __init__(self, id, apiKey):
        if not id:
            raise TypeError('Expected a Custom Search Engine ID')
        if not apiKey:
            raise TypeError('Expected an API key')
        
        self.endpoint = 'https://www.googleapis.com'
        self.apiKey = apiKey
        self.id = id
    
    def search(self, query, options=None):
        if not query:
            raise TypeError('Expected a query')
        
        url = f"{self.endpoint}/customsearch/v1?{self.buildQuery(query, options)}"
        print(url)
        
        response = requests.get(url)
        response.raise_for_status()
        
        items = response.json().get('items', [])
        
        return [
            {
                'type': item['mime'],
                'width': item['image']['width'],
                'height': item['image']['height'],
                'size': item['image']['byteSize'],
                'url': item['link'],
                'thumbnail': {
                    'url': item['image']['thumbnailLink'],
                    'width': item['image']['thumbnailWidth'],
                    'height': item['image']['thumbnailHeight']
                },
                'description': item['snippet'],
                'parentPage': item['image']['contextLink']
            }
            for item in items
        ]
    
    def buildQuery(self, query, options=None):
        options = options or {}
        
        result = {
            'q': query.replace(' ', '+'),
            'searchType': 'image',
            'cx': self.id,
            'key': self.apiKey
        }
        
        if options.get('size'):
            result['imgSize'] = options['size']
        
        if options.get('type'):
            result['imgType'] = options['type']
        
        if options.get('dominantColor'):
            result['imgDominantColor'] = options['dominantColor']
        
        if options.get('colorType'):
            result['imgColorType'] = options['colorType']
        
        if options.get('safe'):
            result['safe'] = options['safe']

        if options.get('count'):
            result['num'] = options['count']
        
        if options.get('start'):
            result['start'] = options['start']
        
        return urlencode(result)
