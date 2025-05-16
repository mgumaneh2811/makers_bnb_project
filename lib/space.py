class Space:
    
    def __init__(self, id, space_name, spaces_description, price_per_night, 
                available_from_date, available_to_date, user_id):
        self.id = id
        self.space_name = space_name
        self.spaces_description = spaces_description
        self.price_per_night = price_per_night
        self.available_from_date = available_from_date
        self.available_to_date = available_to_date
        self.user_id = user_id


    def __repr__(self):
        return f"Space({self.id}, {self.space_name}, {self.spaces_description}, {self.price_per_night}, {self.available_from_date}, {self.available_to_date}, {self.user_id})"
    

    def __eq__(self, other):
        return self.__dict__ == other.__dict__