#!/usr/bin/env python

import sys
import os
import time
import shutil
import locale
import gettext
import re
import commands
import datetime
import pwd # Needed to obtain username (not root)

try:
    import pygtk
    pygtk.require("2.0")
except Exception, detail:
    print detail
    pass
try:
    import gtk
    import gtk.glade
    import gobject
    import pango
except Exception, detail:
    print detail
    sys.exit(1)


class Reconstructor:

    def __init__(self):
        # vars (from Linux Mint)
        self.gladefile = '/usr/lib/linuxmint/mintConstructor/mintConstructor.glade'
        self.iconFile = '/usr/lib/linuxmint/mintConstructor/icon.png'

        self.appName = "MintConstructor"        
        self.mountDir = '/media/cdrom'
        self.tmpDir = "tmp"
        self.tmpPackageDir = "tmp_packages"
        # self.customDir = ""
        # self.createNewProject = False        
        # self.isoFilename = ""
        self.buildLiveCdFilename = ''        
        self.watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.working = None
        self.workingDlg = None        
        self.interactiveEdit = False
        self.pageLiveSetup = 0
        self.pageLiveCustomize = 1
        self.pageLiveBuild = 2
        self.pageFinish = 3        
        self.gnomeBinPath = '/usr/bin/gnome-session'
        self.f = sys.stdout
        self.treeModel = None
        self.treeView = None
        
        # Variables (for Swift Linux)
        self.isoFilename = '/mnt/host/linuxmint-201109-gnome-dvd-32bit.iso'
        self.createNewProject = True
        self.customDir = '/usr/local/bin/swiftconstructor'
        self.userName = pwd.getpwuid(1000)[0] # username
        self.swiftSource = '/home/' + self.userName + '/develop'
        self.swiftDest = self.customDir + '/usr/local/bin/develop'
        self.isoOutput = '/mnt/host/regular.iso'
        
        # Automatically mount /mnt/host
        self.auto_mount() 
        
        # If the base ISO file cannot be found, 
        while os.path.exists(self.isoFilename) == False:
			self.get_iso()
		
		# Copies the contents of the ISO file into self.customDir
        self.setupWorkingDirectory()
        
        # Copy Swift Linux scripts to chroot environment
        # In the chroot environment, the Swift Linux scripts will be at /usr/local/bin/develop
        self.copySwiftScripts()
        
        # launchTerminal function contains chroot
        # Swift Linux bypasses the terminal window
        # chroot command is "chroot /usr/local/bin/swiftconstructor/custom_root/"
        self.goChroot()
        
        # Delete Swift Linux scripts from the chroot environment
        self.deleteSwiftScripts()
        
        self.finish() # End of program

# Automatically mount /mnt/host
    def auto_mount(self):
        os.system ("umount -t vboxsf guest /mnt/host")
        os.system ("mount -t vboxsf guest /mnt/host")
        return
        
# Get the base ISO file
    def get_iso(self):
        print (self.isoFilename + " is missing.")
        print ("Please copy the base ISO file to the /home/(username)/guest")
        print ("directory in your host system.")
        raw_input ("Press Enter to continue")
        self.auto_mount()
        return

# ---------- Setup ---------- #
    def setupWorkingDirectory(self):
        print _("INFO: Setting up working directory...")
        # remaster dir
        if self.createNewProject: # Executed in Swift Linux
            # check for existing directories and remove if necessary
            #if os.path.exists(os.path.join(self.customDir, "remaster")):
            #    print _("INFO: Removing existing Remaster directory...")
            #    os.popen('rm -Rf \"' + os.path.join(self.customDir, "remaster/") + '\"')
            
            if os.path.exists(self.customDir) == True:
                print ("INFO: Removing old " + self.customDir )
                shutil.rmtree(self.customDir)
            
            if os.path.exists(os.path.join(self.customDir, "remaster")) == False:
                print ("INFO: Creating Remaster directory at " + self.customDir )
                os.makedirs(os.path.join(self.customDir, "remaster"))
            # check for iso
            if self.isoFilename == "": # Not executed in Swift Linux
                mntDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
                mntDlg.set_icon_from_file(self.iconFile)
                mntDlg.vbox.set_spacing(10)
                labelSpc = gtk.Label(" ")
                mntDlg.vbox.pack_start(labelSpc)
                labelSpc.show()
                lblText = _("  <b>Please insert the Live CD and click OK</b>  ")
                label = gtk.Label(lblText)
                label.set_use_markup(True)
                mntDlg.vbox.pack_start(label)
                label.show()
                #warnDlg.show()
                response = mntDlg.run()
                if response == gtk.RESPONSE_OK:
                    print _("Using Live CD for remastering...")
                    mntDlg.destroy()
                    os.popen("mount " + self.mountDir)
                else:
                    mntDlg.destroy()
                    self.setDefaultCursor()
                    return
            else: # Executed in Swift Linux
                print _("Using ISO for remastering...")
                os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            print _("Copying files...")

            # copy remaster files
            os.popen('rsync -at --del ' + self.mountDir + '/ \"' + os.path.join(self.customDir, "remaster") + '\"')
            print _("Finished copying files...")

            # unmount iso/cd-rom
            os.popen("umount " + self.mountDir)
        # custom root dir
        if self.createNewProject: # Executed in Swift Linux

            if os.path.exists(os.path.join(self.customDir, "custom_root")) == False:
                print _("INFO: Creating Custom Root directory...")
                os.makedirs(os.path.join(self.customDir, "custom_root"))
            # check for existing directories and remove if necessary
            if os.path.exists(os.path.join(self.customDir, "tmpsquash")):
                print _("INFO: Removing existing tmpsquash directory...")

                os.popen('rm -Rf \"' + os.path.join(self.customDir, "tmpsquash") + '\"')

            # extract squashfs into custom root
            # check for iso
            if self.isoFilename == "": # Not executed in Swift Linux
                mntDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
                mntDlg.set_icon_from_file(self.iconFile)
                mntDlg.vbox.set_spacing(10)
                labelSpc = gtk.Label(" ")
                mntDlg.vbox.pack_start(labelSpc)
                labelSpc.show()
                lblText = _("  <b>Please insert the Live CD and click OK</b>  ")
                label = gtk.Label(lblText)
                label.set_use_markup(True)
                mntDlg.vbox.pack_start(label)
                label.show()
                response = mntDlg.run()
                if response == gtk.RESPONSE_OK:
                    print _("Using Live CD for squashfs root...")
                    mntDlg.destroy()
                    os.popen("mount " + self.mountDir)
                else:
                    mntDlg.destroy()
                    self.setDefaultCursor()
                    return
            else: # Executed in Swift Linux
                print _("Using ISO for squashfs root...")
                os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            # copy remaster files
            os.mkdir(os.path.join(self.customDir, "tmpsquash"))
            # mount squashfs root
            print _("Mounting squashfs...")
            os.popen('mount -t squashfs -o loop ' + self.mountDir + '/casper/filesystem.squashfs \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            print _("Extracting squashfs root...")

            # copy squashfs root
            os.popen('rsync -at --del \"' + os.path.join(self.customDir, "tmpsquash") + '\"/ \"' + os.path.join(self.customDir, "custom_root/") + '\"')

            # umount tmpsquashfs
            print _("Unmounting tmpsquash...")
            os.popen('umount --force \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            # umount cdrom
            print _("Unmounting cdrom...")
            os.popen("umount --force " + self.mountDir)
            # remove tmpsquash
            print _("Removing tmpsquash...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            # set proper permissions - MUST DO WITH UBUNTU
            print _("Setting proper permissions...")
            os.popen('chmod 6755 \"' + os.path.join(self.customDir, "custom_root/usr/bin/sudo") + '\"')
            os.popen('chmod 0440 \"' + os.path.join(self.customDir, "custom_root/etc/sudoers") + '\"')
            print _("Finished extracting squashfs root...")

        # load comboboxes for customization
        #self.hideWorking()
        # self.setDefaultCursor()
        # self.setPage(self.pageLiveCustomize)
        print _("Finished setting up working directory...")
        print " "
        return False

    # Copy Swift Linux scripts to chroot environment
    # In the chroot environment, the Swift Linux scripts will be at /usr/local/bin/develop
    def copySwiftScripts(self):
        # From earlier:
        # self.swiftSource = "/home/" + self.userName + "/develop"
        # self.swiftDest = self.customDir + "/usr/local/bin/develop"
        print ("BEGIN copying Swift Linux scripts to the chroot environment")
        shutil.copytree (self.swiftSource, self.swiftDest)
        print ("FINISHED copying Swift Linux scripts to the chroot environment")
        return

    # Delete Swift Linux scripts from chroot environment
    # In the chroot environment, the Swift Linux scripts are at /usr/local/bin/develop
    def deleteSwiftScripts(self):
        # From earlier:
        # self.swiftDest = self.customDir + "/usr/local/bin/develop"
        print ("BEGIN deleting Swift Linux scripts from the chroot environment")
        shutil.rmtree(self.swiftDest)
        print ("FINISHED deleting Swift Linux scripts from the chroot environment")
        return
		

    # launch chroot terminal
    def goChroot(self):
        try:
            # setup environment
            # copy dns info
            print _("Try: Copying DNS info...")
            os.popen('cp -f /etc/resolv.conf ' + os.path.join(self.customDir, "custom_root/etc/resolv.conf"))
            # mount /proc
            print _("Try: Mounting /proc filesystem...")
            os.popen('mount --bind /proc \"' + os.path.join(self.customDir, "custom_root/proc") + '\"')
            # copy apt.conf
            #print _("Copying apt.conf configuration...")
            #os.popen('cp -f /etc/apt/apt.conf ' + os.path.join(self.customDir, "custom_root/etc/apt/apt.conf"))
            # copy wgetrc
            print _("Try: Copying wgetrc configuration...")
            # backup
            os.popen('mv -f \"' + os.path.join(self.customDir, "custom_root/etc/wgetrc") + '\" \"' + os.path.join(self.customDir, "custom_root/etc/wgetrc.orig") + '\"')
            os.popen('cp -f /etc/wgetrc ' + os.path.join(self.customDir, "custom_root/etc/wgetrc"))
            
            # Execute "chroot /usr/local/bin/swiftconstructor/custom_root"
            # From earlier: self.customDir = "/usr/local/bin/swiftconstructor"
            os.system('chroot ' + self.customDir + '/custom_root')
            os.system('sh /usr/local/bin/develop/1-build/shared-regular.sh')
            os.system('exit')
            
            # restore wgetrc
            print _("Restoring wgetrc configuration...")
            os.popen('mv -f \"' + os.path.join(self.customDir, "root/etc/wgetrc.orig") + '\" \"' + os.path.join(self.customDir, "root/etc/wgetrc") + '\"')
            # remove apt.conf
            #print _("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/apt/apt.conf") + '\"')
            # remove dns info
            print _("Removing DNS info...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/resolv.conf") + '\"')
            # umount /proc
            print _("Umounting /proc...")
            os.popen('umount \"' + os.path.join(self.customDir, "root/proc/") + '\"')

        except Exception, detail: # Not used in Swift Linux
            # restore settings
            # restore wgetrc
            print _("Except: Restoring wgetrc configuration...")
            os.popen('mv -f \"' + os.path.join(self.customDir, "custom_root/etc/wgetrc.orig") + '\" \"' + os.path.join(self.customDir, "custom_root/etc/wgetrc") + '\"')
            # remove apt.conf
            #print _("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "custom_root/etc/apt/apt.conf") + '\"')
            # remove dns info
            print _("Except: Removing DNS info...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "custom_root/etc/resolv.conf") + '\"')
            # umount /proc
            print _("Except: Umounting /proc...")
            os.popen('umount \"' + os.path.join(self.customDir, "custom_root/proc/") + '\"')
            # remove temp script
            os.popen('rm -Rf /tmp/reconstructor-terminal.sh')

            errText = _('Error launching terminal: ')
            print errText, detail
            pass

        return


# ---------- Build ---------- #
    def build(self):
        # Clean remaster/casper directory
        #os.popen("rm -rf %s/remaster/casper/*" % self.customDir)
        
        # Update kernel and initrd
        vmlinuz_filename = commands.getoutput("ls -al %s/root/vmlinuz" % self.customDir).split("/")[-1]
        vmlinuz_path = "%s/root/boot/%s" % (self.customDir, vmlinuz_filename)
        if os.path.exists(vmlinuz_path):                
            os.popen("cp %s %s/remaster/casper/vmlinuz" % (vmlinuz_path, self.customDir))
            print "Updating vmlinuz"
        else:
            print "WARNING: Not updating vmlinuz!!! %s not found!" % vmlinuz_path
            return
        initrd_filename = commands.getoutput("ls -al %s/root/initrd.img" % self.customDir).split("/")[-1]
        initrd_path = "%s/root/boot/%s" % (self.customDir, initrd_filename)
        if os.path.exists(initrd_path):             
            os.popen("cp %s %s/remaster/casper/initrd.lz" % (initrd_path, self.customDir))
            print "Updating initrd"
        else:
            print "WARNING: Not updating initrd!!! %s not found!" % initrd_path
            return
        
        #Update filesystem.size
        os.popen("du -b %(directory)s/root/ 2> /dev/null | tail -1 | awk {'print $1;'} > %(directory)s/remaster/casper/filesystem.size" % {'directory':self.customDir})
                
        # check for custom mksquashfs (for multi-threading, new features, etc.)
        mksquashfs = ''
        if commands.getoutput('echo $MKSQUASHFS') != '':
            mksquashfs = commands.getoutput('echo $MKSQUASHFS')
            print 'Using alternative mksquashfs: ' + ' Version: ' + commands.getoutput(mksquashfs + ' -version')
        # setup build vars                
        self.buildLiveCdFilename = self.wTree.get_widget("entryLiveIsoFilename").get_text()
        self.LiveCdDescription = "Linux Mint"        
        self.hfsMap = os.getcwd() + "/lib/hfs.map"

        print " "
        print _("INFO: Starting Build...")
        print " "

        # build squash root                
        if os.path.exists(os.path.join(self.customDir, "custom_root")):
            print _("Creating SquashFS root...")
            print _("Updating File lists...")
            q = ' dpkg-query -W --showformat=\'${Package} ${Version}\n\' '
            os.popen('chroot \"' + os.path.join(self.customDir, "custom_root/") + '\"' + q + ' > \"' + os.path.join(self.customDir, "remaster/casper/filesystem.manifest") + '\"' )
            os.popen('cp -f \"' + os.path.join(self.customDir, "remaster/casper/filesystem.manifest") + '\" \"' + os.path.join(self.customDir, "remaster/casper/filesystem.manifest-desktop") + '\"')
            # check for existing squashfs root
            if os.path.exists(os.path.join(self.customDir, "remaster/casper/filesystem.squashfs")):
                print _("Removing existing SquashFS root...")
                os.popen('rm -Rf \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')
            print _("Building SquashFS root...")
            # check for alternate mksquashfs
            if mksquashfs == '':
                os.system('mksquashfs \"' + os.path.join(self.customDir, "custom_root/") + '\"' + ' \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')
            else:
                os.system(mksquashfs + ' \"' + os.path.join(self.customDir, "custom_root/") + '\"' + ' \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')

        # build iso       
        if os.path.exists(os.path.join(self.customDir, "remaster")):
            print _("Creating ISO...")
            # update manifest files
            os.system("/usr/lib/linuxmint/mintConstructor/updateManifest.sh " + self.customDir)
            # update md5
            print _("Updating md5 sums...")
            os.system('rm ' + os.path.join(self.customDir, "remaster/") + ' md5sum.txt')
            os.popen('cd \"' + os.path.join(self.customDir, "remaster/") + '\"; ' + 'find . -type f -print0 | xargs -0 md5sum > md5sum.txt')
            #Remove md5sum.txt from md5sum.txt
            os.system("sed -e '/md5sum.txt/d' " + os.path.join(self.customDir, "remaster/") + "md5sum.txt > " + os.path.join(self.customDir, "remaster/") + "md5sum.new")
            os.system("mv " + os.path.join(self.customDir, "remaster/") + "md5sum.new " + os.path.join(self.customDir, "remaster/") + "md5sum.txt")
            #Remove boot.cat from md5sum.txt
            os.system("sed -e '/boot.cat/d' " + os.path.join(self.customDir, "remaster/") + "md5sum.txt > " + os.path.join(self.customDir, "remaster/") + "md5sum.new")
            os.system("mv " + os.path.join(self.customDir, "remaster/") + "md5sum.new " + os.path.join(self.customDir, "remaster/") + "md5sum.txt")
            #Remove isolinux.bin from md5sum.txt
            os.system("sed -e '/isolinux.bin/d' " + os.path.join(self.customDir, "remaster/") + "md5sum.txt > " + os.path.join(self.customDir, "remaster/") + "md5sum.new")
            os.system("mv " + os.path.join(self.customDir, "remaster/") + "md5sum.new " + os.path.join(self.customDir, "remaster/") + "md5sum.txt")
            # remove existing iso
            if os.path.exists(self.buildLiveCdFilename):
                print _("Removing existing ISO...")
                os.popen('rm -Rf \"' + self.buildLiveCdFilename + '\"')
            # build
            # check for description - replace if necessary
            if self.wTree.get_widget("entryLiveCdDescription").get_text() != "":
                self.LiveCdDescription = self.wTree.get_widget("entryLiveCdDescription").get_text()
                
            os.system("echo \"%s\" > %s/iso_name" % (self.LiveCdDescription, self.customDir))

            # build iso according to architecture                
            print _("Building ISO...")
            os.system('genisoimage -o \"' + self.buildLiveCdFilename + '\" -b \"isolinux/isolinux.bin\" -c \"isolinux/boot.cat\" -no-emul-boot -boot-load-size 4 -boot-info-table -V \"' + self.LiveCdDescription + '\" -cache-inodes -r -J -l \"' + os.path.join(self.customDir, "remaster") + '\"')                

        self.setDefaultCursor()
        self.setPage(self.pageFinish)
        # print status message
        statusMsgFinish = _('     <b>Finished.</b>     ')
        statusMsgISO = _('      <b>Finished.</b> ISO located at: ')
        if os.path.exists(self.buildLiveCdFilename):
            print "ISO Located: " + self.buildLiveCdFilename
            self.wTree.get_widget("labelBuildComplete").set_text(statusMsgISO + self.buildLiveCdFilename + '     ')
            self.wTree.get_widget("labelBuildComplete").set_use_markup(True)
        else:
            self.wTree.get_widget("labelBuildComplete").set_text(statusMsgFinish)
            self.wTree.get_widget("labelBuildComplete").set_use_markup(True)
        # enable/disable iso burn
        self.checkEnableBurnIso()

        print "Build Complete..."
        if os.path.exists("/usr/bin/aplay"):
            os.system("/usr/bin/aplay /usr/lib/linuxmint/mintConstructor/done.wav")
                    
    def finish(self):
        # finished... exit
        print ("Exiting...")
        sys.exit(0)



# ---------- MAIN ----------

if __name__ == "__main__":
    APPDOMAIN='reconstructor'
    LANGDIR='lang'
    # locale
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain(APPDOMAIN, LANGDIR)
    gtk.glade.bindtextdomain(APPDOMAIN, LANGDIR)
    gtk.glade.textdomain(APPDOMAIN)
    gettext.textdomain(APPDOMAIN)
    gettext.install(APPDOMAIN, LANGDIR, unicode=1)

    # check credentials
    if os.getuid() != 0 :
        ## show non-root privledge error
        warnDlg = gtk.Dialog(title="mintConstructor", parent=None, flags=0, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK))
        warnDlg.set_icon_from_file('/usr/lib/linuxmint/mintConstructor/icon.png')
        warnDlg.vbox.set_spacing(10)
        labelSpc = gtk.Label(" ")
        warnDlg.vbox.pack_start(labelSpc)
        labelSpc.show()
        warnText = _("  <b>You must run with root privileges.</b>")
        infoText = _("Insufficient permissions")
        label = gtk.Label(warnText)
        lblInfo = gtk.Label(infoText)
        label.set_use_markup(True)
        lblInfo.set_use_markup(True)
        warnDlg.vbox.pack_start(label)
        warnDlg.vbox.pack_start(lblInfo)
        label.show()
        lblInfo.show()
        response = warnDlg.run()
        if response == gtk.RESPONSE_OK :
            warnDlg.destroy()
            #gtk.main_quit()
            sys.exit(0)
        # use gksu to open -- HIDES TERMINAL
        #os.popen('gksu ' + os.getcwd() + '/reconstructor.py')
        #gtk.main_quit()
        #sys.exit(0)
    else :
        rec = Reconstructor()
        # run gui
        gtk.main()
