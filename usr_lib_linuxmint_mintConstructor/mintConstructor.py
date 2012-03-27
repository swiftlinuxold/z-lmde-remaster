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
    
# HOW THIS PROGRAM WORKS

# 1. Set variables

# 2. setupWorkingDirectory
# 2A.  Copy the live CD files to the /usr/local/bin/swiftconstructor/remaster directory.
# 2B.  Install the contents of the booted-up live CD to /usr/local/bin/swiftconstructor/custom_root.
#      This means that the usual directory structure (/bin to /var) is visible there.
# 2C.  Update isolinux/isolinux.cfg and splash.jpg within /usr/local/bin/swiftconstructor/remaster

# 3. goChroot
# 3A.  Set up the chroot environment.
# 3B.  Copy the Swift Linux scripts to the custom_root directory for chroot access.
# 3C.  Execute the Swift Linux scripts as chroot.  This changes the contents of
#      /usr/local/bin/swiftconstructor/custom_root .
# 3D.  Delete the Swift Linux scripts from the custom_root directory.
# 3E.  Remove the chroot environment.

# 4. build
# 4A.  mksquashfs updates /usr/local/bin/swiftconstructor/remaster to reflect changes
#      made to /usr/local/bin/swiftconstructor/custom_root  in goChroot.
# 4B.  Update the md5sum values in md5sum.txt in /usr/local/bin/swiftconstructor/remaster
#      to reflect changes made to the live CD files in step 4A.
# 4C.  Transform the contents of /usr/local/bin/swiftconstructor/remaster into an ISO file.
#      (This is the reverse of step 2A.)

# Replace text in a file        
def change_text (filename, text_old, text_new):
    text=open(filename, 'r').read()
    text = text.replace(text_old, text_new)
    open(filename, "w").write(text)

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
        print ('self.isoFilename: ' + self.isoFilename)
        
        self.createNewProject = True
        print ('self.createNewProject: ' + str(self.createNewProject))
        
        self.customDir = '/usr/local/bin/swiftconstructor'
        print ('self.customDir: ' + self.customDir)
        
        self.chrootDir = self.customDir + '/custom_root'
        print ('self.chrootDir: '+ self.chrootDir)
        
        self.userName = pwd.getpwuid(1000)[0] # username
        print ('self.userName: ' + self.userName)
        
        self.swiftSource = '/home/' + self.userName + '/develop'
        print ('self.swiftSource: ' + self.swiftSource)
        
        self.swiftDest = self.chrootDir + '/usr/local/bin/develop'
        print ('self.swiftDest: ' + self.swiftDest)
        
        self.chrootPrefix = 'chroot '+self.chrootDir+' '
        print ('self.chrootPrefix: ' + self.chrootPrefix) + '(command)'
        
        self.buildLiveCdFilename = '/mnt/host/regular.iso'
        print ('buildLiveCdFilename: ' + self.buildLiveCdFilename)  
        
        # Automatically mount /mnt/host
        self.auto_mount() 
        
        # If the base ISO file cannot be found, 
        while os.path.exists(self.isoFilename) == False:
			self.get_iso()
		
        print ("Ready to work with " + self.isoFilename)
        # Copies the contents of the ISO file into self.customDir
        self.setupWorkingDirectory()
        
        self.update_isolinux()
        
        # launchTerminal function contains chroot
        # Swift Linux bypasses the terminal window
        # chroot command is "chroot /usr/local/bin/swiftconstructor/custom_root/"
        self.goChroot()
                
        # Create the Output ISO file
        self.build()
        
        self.finish() # End of program

# Automatically mount /mnt/host
    def auto_mount(self):
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
        # 2A.  Copy the live CD files to the /usr/local/bin/swiftconstructor/remaster directory.
        print _("INFO: Setting up working directory...")
        # remaster dir
        if self.createNewProject: # Executed in Swift Linux
            # check for existing directories and remove if necessary
            #if os.path.exists(os.path.join(self.customDir, "remaster")):
            #    print _("INFO: Removing existing Remaster directory...")
            #    os.popen('rm -Rf \"' + os.path.join(self.customDir, "remaster/") + '\"')
            
            if os.path.exists(self.customDir) == True:
                print ("INFO: Removing old " + self.customDir )
                os.system ('rm -rf '+self.customDir)
            
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
                # self.isoFilename = '/mnt/host/linuxmint-201109-gnome-dvd-32bit.iso'
                # self.mountDir = '/media/cdrom'
                # print _("Using ISO for remastering...")
                print ("=========================")
                print ("Using ISO for remastering")
                print ("Accessing the live CD files from the ISO")
                print ("Please wait...")
                os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            # print _("Copying files...")
            print ("=============================")
            print ("Copying the live CD files to " + self.customDir + "/remaster")
            print ("Please wait...")
            

            # copy remaster files
            # self.mountDir = '/media/cdrom'
            # self.customDir = '/usr/local/bin/swiftconstructor'
            os.popen('rsync -at --del ' + self.mountDir + '/ \"' + os.path.join(self.customDir, "remaster") + '\"')
            
            #Duplicate /remaster directory
            #if os.path.exists(os.path.join(self.customDir, "remaster2")) == True:
                #shutil.rmtree(os.path.join(self.customDir, "remaster2"))
            #src = self.customDir+'/remaster'
            #dest = self.swiftDest+'/remaster2'
            #shutil.copytree(self.customDir+'/remaster', self.customDir+'/remaster2')
            
            # print _("Finished copying files...")
            print ("======================================")
            print ("Finished copying the live CD files to " + self.mountDir + "/remaster")

            # unmount iso/cd-rom
            os.popen("umount " + self.mountDir)
        
        # 2B.  Install the contents of the booted-up live CD to /usr/local/bin/swiftconstructor/custom_root.
        #      This means that the usual directory structure (/bin to /var) is visible there.
        # custom root dir
        if self.createNewProject: # Executed in Swift Linux

            if os.path.exists(self.chrootDir) == False:
                print _("INFO: Creating Custom Root directory...")
                os.makedirs(self.chrootDir)
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
                #os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            # copy remaster files
            os.mkdir(os.path.join(self.customDir, "tmpsquash"))
            # mount squashfs root (NOTE the "mount -t" instead of "mount -o")
            # print _("Mounting squashfs...")
            print ("Mounting "+self.mountDir+" to tmpsquash...")
            os.popen('mount -t squashfs -o loop ' + self.mountDir + '/casper/filesystem.squashfs \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            # print _("Extracting squashfs root...")
            print ("===========================================")
            print ("Copying files from tmpsquash to custom_root")
            print ("Please wait...")

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
        
    def update_isolinux(self):
		# 2C.  Update isolinux/isolinux.cfg and remove isolinux/splash.jpg within /usr/local/bin/swiftconstructor/remaster
		
        file_splash = self.customDir + '/remaster/isolinux/splash.jpg'
        os.system ('rm ' + file_splash)
		
        file_isolinux = self.customDir + '/remaster/isolinux/isolinux.cfg'
        os.system ('chmod +w ' + file_isolinux) # Make writable
        change_text (file_isolinux, 'Linux Mint Gnome 32-bit (201109)', 'Swift Linux')
        change_text (file_isolinux, 'Linux Mint', 'Swift Linux')
        change_text (file_isolinux, 'menu background splash.jpg', '')
        change_text (file_isolinux, 'DVD', 'CD')
        os.system ('chmod 555 ' + file_isolinux) # Back to the original permissions
		
        return

    # Copy Swift Linux scripts to chroot environment
    # In the chroot environment, the Swift Linux scripts will be at /usr/local/bin/develop
    def copySwiftScripts(self):
        # From earlier:
        # self.swiftSource = '/home/' + self.userName + '/develop'
        # self.swiftDest = self.chrootDir + '/usr/local/bin/develop'
        print ("BEGIN copying Swift Linux scripts to the chroot environment")
        shutil.copytree (self.swiftSource, self.swiftDest)
        print ("FINISHED copying Swift Linux scripts to the chroot environment")
        return

    # Delete Swift Linux scripts from chroot environment
    # In the chroot environment, the Swift Linux scripts are at /usr/local/bin/develop
    def deleteSwiftScripts(self):
        # From earlier:
        # self.swiftDest = self.chrootDir + '/usr/local/bin/develop'
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
            
            # Copy Swift Linux scripts to chroot environment
            # In the chroot environment, the Swift Linux scripts will be at /usr/local/bin/develop
            self.copySwiftScripts()
            
            # Execute "chroot /usr/local/bin/swiftconstructor/custom_root" + command
            # From earlier: self.chrootDir = self.customDir + '/custom_root'
            # From earlier: self.chrootPrefix = 'chroot '+self.chrootDir+' '
                    
            os.system(self.chrootPrefix + 'python /usr/local/bin/develop/1-build/shared-regular.py')
            
            # Delete Swift Linux scripts from the chroot environment
            self.deleteSwiftScripts()
            
            # restore wgetrc
            print _("Restoring wgetrc configuration...")
            os.popen('mv -f \"' + os.path.join(self.customDir, "custom_root/etc/wgetrc.orig") + '\" \"' + os.path.join(self.customDir, "custom_root/etc/wgetrc") + '\"')
            # remove apt.conf
            #print _("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/apt/apt.conf") + '\"')
            # remove dns info
            print _("Removing DNS info...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "custom_root/etc/resolv.conf") + '\"')
            # umount /proc
            print _("Umounting /proc...")
            os.popen('umount \"' + os.path.join(self.customDir, "custom_root/proc/") + '\"')

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
        # 4A.  mksquashfs updates /usr/local/bin/swiftconstructor/remaster to reflect changes in
        #      made to /usr/local/bin/swiftconstructor/custom_root  in goChroot.
        # Clean remaster/casper directory
        #os.popen("rm -rf %s/remaster/casper/*" % self.customDir)
        
        # Update kernel and initrd
        vmlinuz_filename = commands.getoutput("ls -al %s/custom_root/vmlinuz" % self.customDir).split("/")[-1]
        vmlinuz_path = "%s/custom_root/boot/%s" % (self.customDir, vmlinuz_filename)
        # vmlinuz_filename =  vmlinuz-2.6.39-2-486
        # vmlinuz_path = /usr/local/bin/swiftconstructor/custom_root/boot/vmlinuz-2.6.39-2-486
        print ('\nvmlinuz_filename = ' + vmlinuz_filename) 
        print ('vmlinuz_path = ' + vmlinuz_path)
        if os.path.exists(vmlinuz_path):                
            os.popen("cp %s %s/remaster/casper/vmlinuz" % (vmlinuz_path, self.customDir))
            print "Updating vmlinuz"
        else:
            print "WARNING: Not updating vmlinuz!!! %s not found!" % vmlinuz_path
            return
        # initrd_filename = initrd.img-2.6.39-2-486
        # initrd_path = /usr/local/bin/swiftconstructor/custom_root/boot/initrd.img-2.6.39-2-486
        initrd_filename = commands.getoutput("ls -al %s/custom_root/initrd.img" % self.customDir).split("/")[-1]
        initrd_path = "%s/custom_root/boot/%s" % (self.customDir, initrd_filename)
        print ('initrd_filename = ' + initrd_filename)
        print ('initrd_path = ' + initrd_path)
        if os.path.exists(initrd_path):             
            os.popen("cp %s %s/remaster/casper/initrd.lz" % (initrd_path, self.customDir))
            print "Updating initrd"
        else:
            print "WARNING: Not updating initrd!!! %s not found!" % initrd_path
            return
        
        #Update filesystem.size
        os.popen("du -b %(directory)s/custom_root/ 2> /dev/null | tail -1 | awk {'print $1;'} > %(directory)s/remaster/casper/filesystem.size" % {'directory':self.customDir})
                
        # check for custom mksquashfs (for multi-threading, new features, etc.)
        mksquashfs = ''
        if commands.getoutput('echo $MKSQUASHFS') != '':
            mksquashfs = commands.getoutput('echo $MKSQUASHFS')
            print 'Using alternative mksquashfs: ' + ' Version: ' + commands.getoutput(mksquashfs + ' -version')
        # setup build vars                
        # self.buildLiveCdFilename = self.wTree.get_widget("entryLiveIsoFilename").get_text()
        # self.LiveCdDescription = "Linux Mint"        
        self.LiveCdDescription = "Swift Linux"        
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
            # Suppress the progress bar, which makes the log file several MB in size
            print ("NOTE: The mksquashfs process is about to begin.  It will take a LONG time to finish.")
            if mksquashfs == '':
                os.system('mksquashfs -no-progress \"' + os.path.join(self.customDir, "custom_root/") + '\"' + ' \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')
            else:
                os.system(mksquashfs + ' \"' + os.path.join(self.customDir, "custom_root/") + '\"' + ' \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')
        
        # 4B.  Update the md5sum values in md5sum.txt in /usr/local/bin/swiftconstructor/remaster
        #      to reflect changes made to the live CD files in step 4A.
        # build iso       
        if os.path.exists(os.path.join(self.customDir, "remaster")):
            print _("Creating ISO...")
            # update manifest files
            os.system("/usr/lib/linuxmint/mintConstructor/updateManifest.sh " + self.customDir)
            # update md5
            print _("Updating md5 sums...")
            os.system('rm ' + os.path.join(self.customDir, "remaster/") + 'md5sum.txt')
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
                
            os.system("echo \"%s\" > %s/iso_name" % (self.LiveCdDescription, self.customDir))

            # 4C.  Transform the contents of /usr/local/bin/swiftconstructor/remaster into an ISO file.
            #      (This is the reverse of step 2A.)

            # build iso according to architecture                
            print _("Building ISO...")
            
            # GENERATES THE OUTPUT ISO FILE
            os.system('genisoimage -o \"' + self.buildLiveCdFilename + '\" -b \"isolinux/isolinux.bin\" -c \"isolinux/boot.cat\" -no-emul-boot -boot-load-size 4 -boot-info-table -V \"' + self.LiveCdDescription + '\" -cache-inodes -r -J -l \"' + os.path.join(self.customDir, "remaster") + '\"')                

        # print status message
        statusMsgFinish = _('     <b>Finished.</b>     ')
        statusMsgISO = _('      <b>Finished.</b> ISO located at: ')
        if os.path.exists(self.buildLiveCdFilename):
            print "ISO Located: " + self.buildLiveCdFilename

        print "Build Complete..."
        return
        
    # Finished
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
