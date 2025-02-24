from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

__all__ = [
    "UpdateStatistics",
]

OBJECT_FILES = "File(s)"
OBJECT_COLLECTIONS = "Collection(s)"

def _print_fields(*fields) -> None:
    
    for field in fields:
        print(f"{field._verb:<10}\t{field._value:<3} {field._object}")

        
class _Statistic():
    _value: int
    _verb: str
    _object: str

    def __init__(self, verb: str, object = OBJECT_COLLECTIONS):
        self._value = 0
        self._verb = verb
        self._object = object
    
    def inc(self):
        self._value += 1

    def __str__(self) -> str:
        return self._value.__str__()

    def __repr__(self) -> str:
        return self._value.__repr__()


class _LocalStatistic(_Statistic):
    _parent_ref: _Statistic

    def __init__(self, parent: _Statistic):
        super().__init__(verb=parent._verb, object=OBJECT_FILES)
        self._parent_ref = parent

    def inc(self): 
        super().inc()
        self._parent_ref.inc()
        

@dataclass(slots=True)
class UpdateStatistics:
    
    @dataclass(slots=True)
    class LocalStatistics:
        parent: UpdateStatistics
        files_added: _LocalStatistic
        files_modified: _LocalStatistic 
        files_removed: _LocalStatistic 
        files_not_found: _LocalStatistic
        collection_name: str

        def __init__(self, parent: UpdateStatistics, coll_name: str):
            self.parent = parent
            self.files_added = _LocalStatistic(parent.files_added)
            self.files_modified = _LocalStatistic(parent.files_modified)
            self.files_removed = _LocalStatistic(parent.files_removed)
            self.files_not_found = _LocalStatistic(parent.files_not_found)
            self.collection_name = coll_name
        
        def print(self) -> None:
            _print_fields(
                self.files_added,
                self.files_modified,
                self.files_removed,
                self.files_not_found,
            )
       
        def _upadeted_collection(self) -> None:
            if self.files_added or self.files_modified or self.files_removed:
                self.parent.modified_collection(self.collection_name)
        
        def __del__(self):
             pass
    
    colls_added: _Statistic = _Statistic(verb="added")
    colls_removed: _Statistic = _Statistic(verb="removed")
    colls_modified: _Statistic = _Statistic("modified")
    _coll_modified_list: set = field(default_factory=set)
    
    files_added: _Statistic = _Statistic("added", OBJECT_FILES)
    files_modified: _Statistic = _Statistic("modified", OBJECT_FILES)
    files_removed: _Statistic = _Statistic("removed", OBJECT_FILES)
    files_not_found: _Statistic = _Statistic("didn't find", OBJECT_FILES)
    
    
    def local_statistics(self, collection_name: str = "") -> UpdateStatistics.LocalStatistics:
        """creates a empty statistics dict for local statistics, whose updates also update
        the parent Statistic values.

        Returns:
            MutableMapping: _description_
        """
        return UpdateStatistics.LocalStatistics(self, collection_name) 
   
    def modified_collection(self, collection: str) -> None:
        if collection in self._coll_modified_list:
            return

        if collection != "":
            self._coll_modified_list.add(collection)
            
        self.colls_modified.inc()
    
    def print(self) -> None:
        _print_fields(
            self.colls_added,
            self.colls_modified,
            self.colls_removed,
        )
        # 33 = 13 (verb + padding) + 4 (tab) + 3 (value padding) + 1 (space) + 13 (len(Collections(s)))
        print("-"*33)
        _print_fields(
            self.files_added,
            self.files_modified,
            self.files_removed,
            self.files_not_found,
        )