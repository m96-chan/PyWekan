from __future__ import annotations

import json
from enum import IntEnum
from typing import Dict, List
from urllib import request, error


class PyWekanBoardRole(IntEnum):
    """
    Board Role Enum
    This is bit flag
    """
    Normal = 0x0000,
    Admin = 0x0001,
    NoComments = 0x0010,
    CommentOnly = 0x0100


class DetailGetMixIn:
    """
    Get Detail Information of object
    """
    @property
    def _get_detail(self):
        """
        Get object detail information
        :return: The detail Information of object
        """
        raise NotImplementedError


class PyWekanContext:
    """
    Context of Wekan access.
    """
    class WAPIException(Exception):
        def __init__(self, res: error.HTTPError):
            super().__init__()
            self.res = res

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self._token = token

    @property
    def token(self):
        # Todo: ID-Passをコンテキストにして、自動で取りに行く仕組みにしたい。
        return self._token

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def _gen_url(self, url):
        return f"{self.base_url}/{url}"

    def get(self, url: str) -> any:
        req = request.Request(self._gen_url(url), headers=self._headers)
        try:
            with request.urlopen(req) as res:
                return json.loads(res.read().decode("utf-8"))
        except error.HTTPError as e:
            raise self.WAPIException(e)

    def post(self, url: str, data: any) -> any:
        req = request.Request(self._gen_url(url), headers=self._headers, data=json.dumps(data).encode())
        try:
            with request.urlopen(req) as res:
                return json.loads(res.read().decode("utf-8"))
        except error.HTTPError as e:
            raise self.WAPIException(e)

    def put(self, url: str, data: any) -> any:
        req = request.Request(self._gen_url(url), headers=self._headers, data=json.dumps(data).encode(), method="PUT")
        try:
            with request.urlopen(req) as res:
                return json.loads(res.read().decode("utf-8"))
        except error.HTTPError as e:
            raise self.WAPIException(e)

    def delete(self, url: str) -> any:
        req = request.Request(self._gen_url(url), headers=self._headers, method="DELETE")
        try:
            with request.urlopen(req) as res:
                return json.loads(res.read().decode("utf-8"))
        except error.HTTPError as e:
            raise self.WAPIException(e)


class _PyWekanObject:
    """
    Wekan object
    _id: id of object
    raw_data: object raw data
    """

    @property
    def id(self) -> str:
        return self._id

    def __init__(self, _id: str, raw: any, ctx: PyWekanContext):
        self._id = _id
        self._raw_data = raw
        self._ctx = ctx


class PyWekan:

    def __init__(self, ctx: PyWekanContext):
        self._ctx = ctx

    def boards(self) -> List[PyWekanBoard]:
        """
        Get only context Boards
        :return: PyWekanBoard list of context...
        """
        return [
            PyWekanBoard(b['_id'], b, self._ctx)
            for b in self._ctx.get('api/boards')
        ]

    def create_board(self, user_id: str, title: str, **kwargs) -> PyWekanBoard:
        is_admin = kwargs.get("is_admin", True)
        is_active = kwargs.get("is_active", True)
        is_no_comments = kwargs.get("is_no_comments", False)
        is_comment_only = kwargs.get("is_comment_only", False)
        permission = "public" if kwargs.get("public", False) else "private"
        color = kwargs.get("color", "belize")
        arg = {
            "title": title,
            "owner": user_id,
            "isAdmin": is_admin,
            "isActive": is_active,
            "isNoComments": is_no_comments,
            "isCommentOnly": is_comment_only,
            "permission": permission,
            "color": color
        }
        board = self._ctx.post(f"api/boards", arg)
        return PyWekanBoard(board['_id'], board, self._ctx)

    def board(self, board_id: str):
        b = self._ctx.get(f"api/boards/{board_id}")
        return PyWekanBoard(b['_id'], b, self._ctx)

    def users(self):
        return [
            PyWekanUser(u['_id'], u, self._ctx)
            for u in self._ctx.get(f"api/users")
        ]

    def user(self, user_id: str):
        u = self._ctx.get(f"api/users/{user_id}")
        return PyWekanUser(u["_id"], u, self._ctx)


class PyWekanUser(_PyWekanObject):
    """
    Wekan user object
    """
    @property
    def id(self) -> str:
        return self._id

    def __init__(self, _id: str, raw: any, ctx: PyWekanContext):
        super().__init__(_id, raw, ctx)


class PyWekanBoard(_PyWekanObject):
    """
    Wekan board object
    """

    @property
    def title(self) -> str:
        return self._raw_data.get('title')

    def __init__(self, _id: str, raw: any, ctx: PyWekanContext):
        super().__init__(_id, raw, ctx)

    def lists(self) -> List[PyWekanList]:
        return [
            PyWekanList(l['_id'], l, self._ctx, self._id)
            for l in self._ctx.get(f"api/boards/{self._id}/lists")
        ]

    def swim_lanes(self) -> List[PyWekanSwimLane]:
        return [
            PyWekanSwimLane(s['_id'], s, self._ctx, self._id)
            for s in self._ctx.get(f"api/boards/{self._id}/swimlanes")
        ]

    def create_list(self, title: str, **kwargs) -> PyWekanList:
        # Todo: Add option from kwargs
        arg = {**{"title": title}, **kwargs}
        wl = self._ctx.post(f"api/boards/{self._id}/lists", arg)
        return PyWekanList(wl['_id'], wl, self._ctx, self._id)

    def create_swim_lane(self, title: str, **kwargs) -> PyWekanSwimLane:
        # Todo: Add option from kwargs
        arg = {**{"title": title}, **kwargs}
        sl = self._ctx.post(f"api/boards/{self._id}/swimlanes", arg)
        return PyWekanSwimLane(sl['_id'], sl, self._ctx, self._id)

    def join_member(self, user_id: str, role: PyWekanBoardRole) -> None:
        arg = {
            "action": "add",
            "isAdmin": role & PyWekanBoardRole.Admin > 0,
            "isNoComments": role & PyWekanBoardRole.NoComments > 0,
            "isCommentOnly": role & PyWekanBoardRole.CommentOnly > 0,
        }
        self._ctx.post(f"api/boards/{self._id}/members/{user_id}/add", arg)

    def remove(self):
        self._ctx.delete(f"api/boards/{self._id}")


class PyWekanSwimLane(_PyWekanObject):
    """
    Wekan swimlane object
    """
    @property
    def title(self) -> str:
        return self._raw_data.get('title')

    def __init__(self, _id: str, raw: any, ctx: PyWekanContext, board_id: str):
        super().__init__(_id, raw, ctx)
        self.board_id = board_id

    def remove(self):
        self._ctx.delete(f"api/boards/{self.board_id}/swimlanes/{self.id}")


class PyWekanList(_PyWekanObject):
    """
    Wekan list object
    """
    @property
    def title(self) -> str:
        return self._raw_data.get('title')

    def __init__(self, _id: str, raw: any, ctx: PyWekanContext, board_id: str):
        super().__init__(_id, raw, ctx)
        self.board_id = board_id

    def create_card(self, title: str, author_id: str, swimlane_id: str, **kwargs) -> PyWekanCard:
        # Todo: Add option from kwargs
        arg = {**{"title": title, "authorId": author_id, "swimlaneId": swimlane_id}, **kwargs}
        wc = self._ctx.post(f"api/boards/{self.board_id}/lists/{self._id}/cards", arg)
        return PyWekanCard(wc['_id'], wc, self._ctx, self.board_id, self._id)

    def cards(self):
        return [
            PyWekanCard(c['_id'], c, self._ctx, self.board_id, self._id)
            for c in self._ctx.get(f"api/boards/{self.board_id}/lists/{self._id}/cards")
        ]

    def remove(self):
        self._ctx.delete(f"api/boards/{self.board_id}/lists/{self._id}")


class PyWekanCard(_PyWekanObject):
    """
    Wekan Card object
    """
    @property
    def title(self) -> str:
        return self._raw_data.get('title')

    def __init__(self, _id: str, raw: any, ctx: PyWekanContext, board_id: str, list_id: str):
        super().__init__(_id, raw, ctx)
        self.board_id = board_id
        self.list_id = list_id

    def remove(self):
        self._ctx.delete(f"api/boards/{self.board_id}/lists/{self.list_id}/cards/{self._id}")
