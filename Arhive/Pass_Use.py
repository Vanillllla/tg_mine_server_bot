class Config:
    @property
    def PASSWORD(self):
        return os.getenv('REGISTRATION_PASSWORD')  # Всегда свежее значение

config = Config()