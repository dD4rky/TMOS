class Response():
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class DataStorageResponse(Response):
    def __init__(self, 
                 positions : dict,
                 orders : list,
                 order_book : dict):
        super().__init__(positions=positions, 
                         orders=orders, 
                         order_book=order_book)

class Request():
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__dict__[key] = value

class DataStorageRequest(Request):
    def __init__(self, 
                 figi : str,
                 positions : bool = False,
                 orders : bool = False,
                 order_book : bool = False):
        super().__init__(figi=figi, 
                         positions=positions,
                         orders=orders, 
                         order_book=order_book)