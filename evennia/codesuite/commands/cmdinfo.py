import re, datetime
from . command import MuxCommand
from .. lib.penn import header,table,cemit,STAFFREP,msghead
from .. lib.charmatch import charmatch
from .. lib.EVInfo.models import InfoFile
from src.objects.models import ObjectDB
from ..lib.align import PrettyTable

class CmdInfo(MuxCommand):
    """
    The Info system allows Players to store notes about their character. These
    notes can be used for a number of things, such as tracking details of
    resources, backgrounds, cheat sheets, or other notes that might be several
    paragraphs in length.

    Many commands allow for a character to be targeted. If not included, the
    target will be yourself. Only Characters can have +infos, so be @ic if you
    want to easily set your own files. Only admin may modify another's info files.

    <list|of|files> is a series of info file names, seperated by pipes. When
    more than one file is included, the command will be run for each filename.
    This can be used for mass setting, viewing, deletion, approval, etc.
    
    Info File names are limited to 18 alphanumeric characters. Partial martches
    are acceptable for anything but setting a file's contents - but it will key
    off of the first possible match. Be wary.
    
    VIEWING INFOS:
    +info [<character>/]
    This will show you your own +info files or those of another, provided they
    are visible to you. Staff may view all files, published or not.

    +info [<character>/]<list|of|files>
    This will display the contents of a file(s).

    +info/get [<character>/]<list|of|files>
    Shows an unformatted text for easy editing of an +info file.

    +info/published
    Shows all characters who have published Info files.

    MANAGING INFOS:
    +info [<character>/]<list|of|files>=<contents>
    Creates a new file, or overwrites an existing one with new contents.

    +info/delete [<character>/]<list|of|files>
    Deletes one or more files. Seperate each name with a pipe symbol!

    +info/publish [<character>/]<list|of|files>
    +info/unpublish [<character>/]<list|of|files>
    Used to publish or hide info files. Multiple files can be published at once
    by seperating their names with the pipe symbol.

    +info/approve [<character>/]<list|of|files>
    +info/unapprove [<character>/]<list|of|files>
    Approves or unapproves a character's files. Only staff may use this. As with
    publish, it can be used to target multiple files if they are seperated by
    pipes.

    OTHER:
    +info/categories
    Displays a list of common or suggested filenames for the game. Using these
    names for the appropriate topics will make it easier on staff.
    """
    
    key = "+info"
    locks = "cmd:all()"
    help_category = "Player"
    
    def func(self):
        caller = self.caller
        switches = self.switches
        rhs = self.rhs
        lhs = self.lhs
        self.sysname = "INFO"
        isadmin = self.isadmin
        playswitches = ['set','delete','publish','unpublish','published','get']
        admswitches = ['approve','unapprove']
        
        if isadmin:
            callswitches = playswitches + admswitches
        else:
            callswitches = playswitches
        switches = self.partial(switches,callswitches)
        
        self.target, self.filelist = self.target_character(lhs)

        if not self.target:
            caller.msg(msghead(self.sysname,error=True) + "Target not found.")
            return

        if str(type(self.target)) == 'Player':
            caller.msg(msghead(self.sysname,error=True) + "Targets must be Characters.")
            return
        
        if "approve" in switches and isadmin:
            self.switch_approve(self.target,self.filelist)
        elif "unapprove" in switches and isadmin:
            self.switch_unapprove(self.target,self.filelist)
        elif "set" in switches or (not switches and self.filelist and rhs):
            self.switch_set(self.target,self.filelist,rhs)
        elif "delete" in switches:
            self.switch_delete(self.target,self.filelist)
        elif "get" in switches:
            self.switch_get(self.target,self.filelist)
        elif "published" in switches:
            self.switch_published()
        elif "publish" in switches:
            self.switch_publish(self.target,self.filelist)
        elif "unpublish" in switches:
            self.switch_unpublish(self.target,self.filelist)
        elif "categories" in switches:
            self.switch_categories()
        elif not switches:
            self.switch_view(self.target,self.filelist)
        else:
            string = "Unrecognized Input. See help +info"
            caller.msg(msghead(self.sysname,error=True) + string)

    def target_character(self,input):
        if "/" in input:
            ststring = input.split("/",1)
            target = charmatch(self.caller,ststring[0])
            if not len(ststring[1]):
                filelist = None
            else:
                filelist = ststring[1].split("|")
        else:
            if not len(input):
                filelist = None
            else:
                filelist = input.split("|")
            target = self.caller
        return target, filelist
    
    def info_list(self,target):
        # This function returns a queryset of info files self.caller can see.
        if self.isadmin:
            return InfoFile.objects.filter(cid=target.dbobj)
        elif target.access(self.player, 'puppet'):
            return InfoFile.objects.filter(cid=target.dbobj,hidden=False)
        else:
            return InfoFile.objects.filter(cid=target.dbobj,hidden=False,published=True)

    def switch_set(self,target,filelist,rhs):
        if not filelist:
            string = "No files entered to set."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if self.caller is not target and not isadmin:
            string = "You may not set that person's files."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not rhs:
            string = "No info file contents entered to set."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        for info in filelist:
            infoname = info.strip()
            file,created = InfoFile.objects.get_or_create(cid=self.target.dbobj,title__iexact=infoname)
            
            if not re.match('^[\w-]+$', infoname):
                string = "File '%s' could not be set: info names must be alphanumeric." % info.strip()
                self.caller.msg(msghead(self.sysname,error=True) + string)
            elif len(infoname) > 18:
                string = "Info File names may not exceed 18 characters."
                self.caller.msg(msghead(self.sysname,error=True) + string)
            elif file.approved:
                string = "File '%s' could not be set: file is approved." % file.title
                self.caller.msg(msghead(self.sysname,error=True) + string)
            elif file.hidden and not self.isadmin:
                string = "You shouldn't have done that, Dave."
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                file.title = infoname
                file.text = rhs
                file.setby = self.player.dbobj
                file.seton = datetime.datetime.now()
                file.save()
                if target in self.player.db._playable_characters:
                    string = "Info File '%s' set!" % info.strip()
                    self.caller.msg(msghead(self.sysname) + string)
                else:
                    string = "Info File '%s' set!" % info.strip()
                    self.caller.msg(msghead(self.sysname) + string)
                    string = "%s set your '%s' info file!" % (self.caller.key, info.strip())
                    target.msg(msghead(self.sysname) + string)

    def switch_delete(self,target,filelist):
        if not filelist:
            string = "No files entered to delete."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not target.access(self.player, 'puppet') and not self.isadmin:
            string = "You may not delete that character's files."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        files = self.info_list(target)
        for info in filelist:
            infoname = info.strip()
            file = files.filter(title__istartswith=infoname)
            if file: file = file[0]
            if not file:
                string = "File '%s' not found." % infoname
                self.caller.msg(msghead(self.sysname,error=True) + string)
            elif file.approved:
                string = "File '%s' could not be deleted: file is approved." % file.title
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                if target in self.player.db._playable_characters:
                    string = "Info File '%s' deleted!" % file.title
                    self.caller.msg(msghead(self.sysname) + string)
                else:
                    string = "Info File '%s' deleted!" % file.title
                    self.caller.msg(msghead(self.sysname) + string)
                    string = "%s deleted your '%s' info file!" % (self.caller.key, file.title)
                    target.msg(msghead(self.sysname) + string)
                file.delete()

    def switch_approve(self,target,filelist):
        if not filelist:
            string = "No files entered to approve."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        files = self.info_list(target)
        for info in filelist:
            infoname = info.strip()
            file = files.filter(title__istartswith=infoname)
            if file: file = file[0]
            if not file:
                string =  "File '%s' not found." % infoname
                self.caller.msg(msghead(self.sysname,error=True) + string) 
            elif file.approved:
                string = "File '%s'is already approved." % file.title
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                file.approved = True
                file.approvedby = self.player.dbobj
                file.approvedon = datetime.datetime.now()
                file.save()
                if target in self.player.db._playable_characters:
                    string = "Info File '%s' approved!" % file.title
                    self.caller.msg(msghead(self.sysname) + string)
                else:
                    string = "Info File '%s' approved!" % file.title
                    self.caller.msg(msghead(self.sysname) + string)
                    string = "%s approved your '%s' info file!" % (self.caller.key, file.title)
                    target.msg(msghead(self.sysname) + string)
    
    def switch_unapprove(self,target,filelist):
        if not filelist:
            string = "No files entered to unapprove."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        files = self.info_list(target,self.isadmin)
        for info in filelist:
            infoname = info.strip()
            file = files.filter(title__istartswith=infoname)
            if file: file = file[0]
            if not file:
                string = "File '%s' not found." % infoname
                self.caller.msg(msghead(self.sysname,error=True) + string)
            elif not file.approved:
                string = "File '%s' is not approved." % file.title
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                file.approved = False
                del file.approvedby
                del file.approvedon
                file.save()
                if target in self.player.db._playable_characters:
                    string = "Info File '%s' unapproved!" % file.title
                    self.caller.msg(msghead(self.sysname) + string)
                else:
                    string = "Info File '%s' unapproved!" % file.title
                    self.caller.msg(msghead(self.sysname) + string)
                    string = "%s unapproved your '%s' info file!" % (self.caller.key, file.title)
                    target.msg(msghead(self.sysname) + string)

    def switch_publish(self,target,filelist):
        if not target.access(self.player, 'puppet') and not self.isadmin:
            string = "You may not publish that person's files."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not filelist:
            string = "No files entered to publish."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        for info in filelist:
            infoname = info.strip()
            file = InfoFile.objects.filter(cid=target.dbobj,title__istartswith=infoname)
            if file: file = file[0]
            if not file:
                string = "File '%s' not found." % infoname
                self.caller.msg(msghead(self.sysname,error=True) + string) 
            elif file.published:
                string = "File '%s' is already published." % file.title
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                file.published = True
                if target in self.player.db._playable_characters:
                    self.caller.msg("Info File '%s' published!" % file.title)
                else:
                    self.caller.msg("Info File '%s' published!" % file.title)
                    target.msg("%s published your '%s' info file!" % (self.caller.key, file.title))
                file.save()

    def switch_unpublish(self,target,filelist):
        if not target.access(self.player, 'puppet') and not self.isadmin:
            string = "You may not unpublish that person's files."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        if not filelist:
            string = "No files entered to unpublish."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        for info in filelist:
            infoname = info.strip()
            file = InfoFile.objects.filter(cid=target.dbobj,title__istartswith=infoname)
            if file: file = file[0]
            if not file:
                string = "File '%s' not found." % infoname
                self.caller.msg(msghead(self.sysname,error=True) + string) 
            elif not file.published:
                string = "File '%s' is not published." % file.title
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                file.published = False
                if target in self.player.db._playable_characters:
                    self.caller.msg("Info File '%s' unpublished!" % file.title)
                else:
                    self.caller.msg("Info File '%s' unpublished!" % file.title)
                    target.msg("%s unpublished your '%s' info file!" % (self.caller.key, file.title))
                file.save()
                
    def switch_view(self,target,filelist):
        files = self.info_list(target)
        if not filelist:
            formatted = []
            for info in files:
                if info.hidden:
                    hidden = "{x"
                else:
                    hidden = "{n"
                if info.published:
                    published = "({wP{n)"
                else:
                    published = ""
                if info.approved:
                    approved = "({w+{n)"
                else:
                    approved = ""
                formatted.append(hidden + info.title + "{n" + published + approved)
            legend = "Legend: + - approved, P - Published"
            infotable = table(formatted,24,78)
            self.caller.msg("\n".join([header("%s's Info Files" % target.key),infotable,header(legend)]))
        else:
            for info in filelist:
                infoname = info.strip()
                file = files.filter(title__istartswith=infoname)
                if not file:
                    string = "File '%s' not found!" % infoname
                    self.caller.msg(msghead(self.sysname,error=True) + string)
                else:
                    file = file[0]
                    lastsetby = "{wLast set by:{n %s {wOn:{n %s" % (file.setby.key,file.seton.ctime())
                    if file.approved:
                        approvedby = "{wApproved by:{n %s {wOn:{n %s" % (file.approvedby.key,file.approvedon.ctime())
                        self.caller.msg("\n".join([header("%s's Info File: %s" % (target.key,file.title)),file.text,header(),lastsetby,approvedby,header()]))
                    else:
                        self.caller.msg("\n".join([header("%s's Info File: %s" % (target.key,file.title)),file.text,header(),lastsetby,header()]))

    def switch_get(self,target,filelist):
        if not filelist:
            string = "No files entered to retrieve."
            self.caller.msg(msghead(self.sysname,error=True) + string)
            return
        for info in filelist:
            infoname = info.strip()
            file = files.filter(title__istartswith=infoname)
            if not file:
                string = "File '%s' not found!" % infoname
                self.caller.msg(msghead(self.sysname,error=True) + string)
            else:
                file = file[0]
                lastsetby = "{wLast set by:{n %s {wOn:{n %s" % (file.setby.key,file.seton.ctime())
                if file.approved:
                    approvedby = "{wApproved by:{n %s {wOn:{n %s" % (file.approvedby.key,file.approvedon.ctime())
                    self.caller.msg(header("%s's Info File: %s" % (target.key,file.title)))
                    self.caller.msg(file.text)
                    self.caller.msg("\n".join([header(),lastsetby,approvedby,header()]))
                else:
                    self.caller.msg(header("%s's Info File: %s" % (target.key,file.title)))
                    self.caller.msg(file.text)
                    self.caller.msg("\n".join([header(),lastsetby,header()]))

    def switch_categories(self):
        self.caller.msg()

    def switch_published(self):
        charlist1 = InfoFile.objects.filter(published=True).values_list('cid',flat=True).distinct()
        charlist2 = ObjectDB.objects.filter(id__in=charlist1)
        
        if not len(charlist2):
            string = "No characters have published info files."
            self.caller.msg(msghead(self.sysname) + string)
            return
        
        table = PrettyTable(['Character','Files','Total'])
        table.align = 'l'
        table.max_width['Character'] = 20
        table.max_width['Files'] = 50
        
        for char in charlist2:
            files = InfoFile.objects.filter(cid=char,published=True).values_list('title',flat=True)
            print files
            table.add_row([char.key,", ".join(files),len(files)])
        
        self.caller.msg(table)