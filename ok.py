# magic ops for learning purpose
from httpx import ReadTimeout
class Emp:
    def __init__(self, **kwargs):
        self.data = kwargs
    
    def __str__(self):
        out = ""
        for key, value in self.data.items():
            out = out + f"{key}: {value} \n"
        return out
    
    def __add__(self, e2):
        if isinstance(e2, Emp):
            return e2.data.get("empid") + self.data.get("empid")

print(Emp(empid=1, name="Rohan", dept="IT") + Emp(empid=2, name="ohan", dept="IT"))