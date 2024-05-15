from typing import Literal
import asyncio

"""
    history:
        {
            type: User or Bot
            message: string
        }
"""

userList = {}


class User:
    def __init__(self, userID: str):
        self.userID = userID
        self.history = []
        userList[userID] = self

    def addHistory(self, type : Literal['Bot', 'User'], message : str):
        self.history.append({'type': type, 'message': message})

