class PlayerType:
    def __init__(self, type: str = None):
        self.type = type if type else "CPU"

    def __repr__(self):
        return self.type

class Controller:
    """
    Represents a physical controller.
    Unique ID is now the device path.
    """

    NUMBER_OF_CONTROLLERS = 0

    def __new__(cls, *args, **kwargs):
        cls.NUMBER_OF_CONTROLLERS += 1
        return super().__new__(cls)

    def __init__(self, vendor_id, product_id, device_path, name=None, transport=None):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device_path = device_path
        self.name = name or f"Controller-{Controller.NUMBER_OF_CONTROLLERS}"
        self.transport = transport

    @property
    def unique_id(self):
        return self.device_path

    def __repr__(self):
        return f"<Controller {self.name} ({self.vendor_id:04X}:{self.product_id:04X})>"
