from . command import MuxCommand
from src.players.models import PlayerDB
from src.utils import utils, gametime
from .. lib.align import PrettyTable


class CmdAccountList(MuxCommand):

    key = "+accounts"
    locks = "cmd:perm(Wizards)"
    
    def func(self):

        plyrs = PlayerDB.objects.all()
        latesttable = PrettyTable(["dbref","name","perms","characters"])
        latesttable.align = 'l'
        latesttable.max_width["name"] = 20
        latesttable.max_width["perms"] = 15
        latesttable.max_width["characters"] = 35
        for ply in plyrs:
            charlist = []
            for char in ply.db._playable_characters:
                charlist.append(char.key)
            latesttable.add_row([ply.dbref, ply.key,", ".join(ply.permissions),", ".join(charlist)])
        self.caller.msg(latesttable)