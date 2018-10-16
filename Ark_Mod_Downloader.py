import arkit
import sys
import os
import argparse
import shutil
import subprocess
from collections import OrderedDict
import struct
import urllib.request
import zipfile

class ArkModDownloader():

    def __init__(self, steamcmd, modids, working_dir, mod_update, modname, preserve=False):

        # I not working directory provided, check if CWD has an ARK server.
        self.working_dir = working_dir
        if not working_dir:
            self.working_dir_check()

        self.steamcmd = steamcmd  # Path to SteamCMD exe

        if not self.steamcmd_check():
            print("SteamCMD Not Found And We Were Unable To Download It")
            sys.exit(0)

        self.modname = modname
        self.installed_mods = []  # List to hold installed mods
        self.map_names = []  # Stores map names from mod.info
        self.meta_data = OrderedDict([])  # Stores key value from modmeta.info
        self.temp_mod_path = os.path.join(os.path.dirname(self.steamcmd), r"steamapps\workshop\content\346110")
        self.preserve = preserve

        self.prep_steamcmd()

        if mod_update:
            print("[+] Mod Update Is Selected.  Updating Your Existing Mods")
            self.update_mods()

        # If any issues happen in download and extract chain this returns false
        if modids:
            for mod in modids:
                if self.download_mod(mod):
                    if self.move_mod(mod):
                        print("[+] Mod {} Installation Finished".format(str(mod)))
                else:
                    print("[+] There was as problem downloading mod {}.  See above errors".format(str(mod)))

    def create_mod_name_txt(self, mod_folder, modid):
        print(os.path.join(mod_folder, self.map_names[0] + " - " + modid + ".txt"))
        with open(os.path.join(mod_folder, self.map_names[0] + ".txt"), "w+") as f:
            f.write(modid)

    def working_dir_check(self):
        print("[!] No working directory provided.  Checking Current Directory")
        print("[!] " + os.getcwd())
        if os.path.isdir(os.path.join(os.getcwd(), "ShooterGame\Content")):
            print("[+] Current Directory Has Ark Server.  Using The Current Directory")
            self.working_dir = os.getcwd()
        else:
            print("[x] Current Directory Does Not Contain An ARK Server. Aborting")
            sys.exit(0)

    def steamcmd_check(self):
        """
        If SteamCMD path is provided verify that exe exists.
        If no path provided check TCAdmin path working dir.  If not located try to download SteamCMD.
        :return: Bool
        """

        # Check provided directory
        if self.steamcmd:
            print("[+] Checking Provided Path For SteamCMD")
            if os.path.isfile(os.path.join(self.steamcmd, "steamcmd.exe")):
                self.steamcmd = os.path.join(self.steamcmd, "steamcmd.exe")
                print("[+] SteamCMD Found At Provided Path")
                return True

        # Check TCAdmin Directory
        print("[+] SteamCMD Location Not Provided. Checking Common Locations")
        if os.path.isfile(r"C:\Program Files\TCAdmin2\Monitor\Tools\SteamCmd\steamcmd.exe"):
            print("[+] SteamCMD Located In TCAdmin Directory")
            self.steamcmd = r"C:\Program Files\TCAdmin2\Monitor\Tools\SteamCmd\steamcmd.exe"
            return True

        # Check working directory
        if os.path.isfile(os.path.join(self.working_dir, "SteamCMD\steamcmd.exe")):
            print("[+] Located SteamCMD")
            self.steamcmd = os.path.join(self.working_dir, "SteamCMD\steamcmd.exe")
            return True

        print("[+} SteamCMD Not Found In Common Locations. Attempting To Download")

        try:
            with urllib.request.urlopen("https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip") as response:
                if not os.path.isdir(os.path.join(self.working_dir, "SteamCMD")):
                    os.mkdir(os.path.join(self.working_dir, "SteamCMD"))

                steam_cmd_zip = os.path.join(self.working_dir, "steamcmd.zip")
                with open(steam_cmd_zip, "w+b") as output:
                    output.write(response.read())

                zip_file = zipfile.ZipFile(steam_cmd_zip)
                try:
                    zip_file.extractall(os.path.join(self.working_dir, "SteamCMD"))
                except zipfile.BadZipfile as e:
                    print("[x] Failed To Extract steamcmd.zip. Aborting")
                    print("[x] Error: " + e)
                    sys.exit()

        except urllib.request.HTTPError as e:
            print("[x] Failed To Download SteamCMD. Aborting")
            print("[x] ERROR: " + e)
            return False

        self.steamcmd = os.path.join(self.working_dir, r"SteamCMD\steamcmd.exe")

        return True

    def prep_steamcmd(self):
        """
        Delete steamapp folder to prevent Steam from remembering it has downloaded this mod before
        This is mainly for game hosts.  Example, hosts using TCAdmin have one SteamCMD folder. If mod was downloaded
        by another customer SteamCMD will think it already exists and not download again.
        :return:
        """

        if self.preserve:
            return

        steamapps = os.path.join(os.path.dirname(self.steamcmd), "steamapps")

        if os.path.isdir(steamapps):
            print("[+] Removing Steamapps Folder")
            try:
                shutil.rmtree(steamapps)
            except OSError:
                """
                If run on a TCAdmin server using TCAdmin's SteamCMD this may prevent mod from downloading if another
                user has downloaded the same mod.  This is due to SteamCMD's cache.  It will think this mod has is
                already installed and up to date.
                """
                print("[x] Failed To Remove Steamapps Folder. This is normally okay.")
                print("[x] If this is a TCAdmin Server and using the TCAdmin SteamCMD it may prevent mod from downloading")

    def update_mods(self):
        self.build_list_of_mods()
        if self.installed_mods:
            for mod in self.installed_mods:
                print("[+] Updating Mod " + mod)
                if not self.download_mod(mod):
                    print("[x] Error Updating Mod " + mod)
        else:
            print("[+] No Installed Mods Found.  Skipping Update")

    def build_list_of_mods(self):
        """
        Build a list of all installed mods by grabbing all directory names from the mod folder
        :return:
        """
        if not os.path.isdir(os.path.join(self.working_dir, "ShooterGame\Content\Mods")):
            return
        for curdir, dirs, files in os.walk(os.path.join(self.working_dir, "ShooterGame\Content\Mods")):
            for d in dirs:
                self.installed_mods.append(d)
            break

    def download_mod(self, modid):
        """
        Launch SteamCMD to download ModID
        :return:
        """
        print("[+] Starting Download of Mod " + str(modid))
        args = []
        args.append(self.steamcmd)
        args.append("+login anonymous")
        args.append("+workshop_download_item")
        args.append("346110")
        args.append(modid)
        args.append("+quit")
        subprocess.call(args, shell=True)

        return True if self.extract_mod(modid) else False


    def extract_mod(self, modid):
        """
        Extract the .z files using the arkit lib.
        If any file fails to download this whole script will abort
        :return: None
        """

        print("[+] Extracting .z Files.")

        try:
            for curdir, subdirs, files in os.walk(os.path.join(self.temp_mod_path, modid, "WindowsNoEditor")):
                for file in files:
                    name, ext = os.path.splitext(file)
                    if ext == ".z":
                        src = os.path.join(curdir, file)
                        dst = os.path.join(curdir, name)
                        uncompressed = os.path.join(curdir, file + ".uncompressed_size")
                        arkit.unpack(src, dst)
                        #print("[+] Extracted " + file)
                        os.remove(src)
                        if os.path.isfile(uncompressed):
                            os.remove(uncompressed)

        except (arkit.UnpackException, arkit.SignatureUnpackException, arkit.CorruptUnpackException) as e:
            print("[x] Unpacking .z files failed, aborting mod install")
            return False

        if self.create_mod_file(modid):
            if self.move_mod(modid):
                return True
            else:
                return False


    def move_mod(self, modid):
        """
        Move mod from SteamCMD download location to the ARK server.
        It will delete an existing mod with the same ID
        :return:
        """

        ark_mod_folder = os.path.join(self.working_dir, "ShooterGame\Content\Mods")
        output_dir = os.path.join(ark_mod_folder, str(modid))
        source_dir = os.path.join(self.temp_mod_path, modid, "WindowsNoEditor")

        # TODO Need to handle exceptions here
        if not os.path.isdir(ark_mod_folder):
            print("[+] Creating Directory: " + ark_mod_folder)
            os.mkdir(ark_mod_folder)

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

        print("[+] Moving Mod Files To: " + output_dir)
        shutil.copytree(source_dir, output_dir)

        if self.modname:
            print("Creating Mod Name File")
            self.create_mod_name_txt(ark_mod_folder, modid)

        return True

    def create_mod_file(self, modid):
        """
        Create the .mod file.
        This code is an adaptation of the code from Ark Server Launcher.  All credit goes to Face Wound on Steam
        :return:
        """
        if not self.parse_base_info(modid) or not self.parse_meta_data(modid):
            return False

        print("[+] Writing .mod File")
        with open(os.path.join(self.temp_mod_path, modid, r"WindowsNoEditor\.mod"), "w+b") as f:

            modid = int(modid)
            f.write(struct.pack('ixxxx', modid))  # Needs 4 pad bits
            self.write_ue4_string("ModName", f)
            self.write_ue4_string("", f)

            map_count = len(self.map_names)
            f.write(struct.pack("i", map_count))

            for m in self.map_names:
                self.write_ue4_string(m, f)

            # Not sure of the reason for this
            num2 = 4280483635
            f.write(struct.pack('I', num2))
            num3 = 2
            f.write(struct.pack('i', num3))

            if "ModType" in self.meta_data:
                mod_type = b'1'
            else:
                mod_type = b'0'

            # TODO The packing on this char might need to be changed
            f.write(struct.pack('p', mod_type))
            meta_length = len(self.meta_data)
            f.write(struct.pack('i', meta_length))

            for k, v in self.meta_data.items():
                self.write_ue4_string(k, f)
                self.write_ue4_string(v, f)

        return True

    def read_ue4_string(self, file):
        count = struct.unpack('i', file.read(4))[0]
        flag = False
        if count < 0:
            flag = True
            count -= 1

        if flag or count <= 0:
            return ""

        return file.read(count)[:-1].decode()

    def write_ue4_string(self, string_to_write, file):
        string_length = len(string_to_write) + 1
        file.write(struct.pack('i', string_length))
        barray = bytearray(string_to_write, "utf-8")
        file.write(barray)
        file.write(struct.pack('p', b'0'))

    def parse_meta_data(self, modid):
        """
        Parse the modmeta.info files and extract the key value pairs need to for the .mod file.
        How To Parse modmeta.info:
            1. Read 4 bytes to tell how many key value pairs are in the file
            2. Read next 4 bytes tell us how many bytes to read ahead to get the key
            3. Read ahead by the number of bytes retrieved from step 2
            4. Read next 4 bytes to tell how many bytes to read ahead to get value
            5. Read ahead by the number of bytes retrieved from step 4
            6. Start at step 2 again
        :return: Dict
        """

        print("[+] Collecting Mod Meta Data From modmeta.info")
        print("[+] Located The Following Meta Data:")

        mod_meta = os.path.join(self.temp_mod_path, modid, r"WindowsNoEditor\modmeta.info")
        if not os.path.isfile(mod_meta):
            print("[x] Failed To Locate modmeta.info. Cannot continue without it.  Aborting")
            return False

        with open(mod_meta, "rb") as f:

            total_pairs = struct.unpack('i', f.read(4))[0]

            for i in range(total_pairs):

                key, value = "", ""

                key_bytes = struct.unpack('i', f.read(4))[0]
                key_flag = False
                if key_bytes < 0:
                    key_flag = True
                    key_bytes -= 1

                if not key_flag and key_bytes > 0:

                    raw = f.read(key_bytes)
                    key = raw[:-1].decode()

                value_bytes = struct.unpack('i', f.read(4))[0]
                value_flag = False
                if value_bytes < 0:
                    value_flag = True
                    value_bytes -= 1

                if not value_flag and value_bytes > 0:
                    raw = f.read(value_bytes)
                    value = raw[:-1].decode()

                # TODO This is a potential issue if there is a key but no value
                if key and value:
                    print("[!] " + key + ":" + value)
                    self.meta_data[key] = value

        return True


    def parse_base_info(self, modid):

        print("[+] Collecting Mod Details From mod.info")

        mod_info = os.path.join(self.temp_mod_path, modid, r"WindowsNoEditor\mod.info")

        if not os.path.isfile(mod_info):
            print("[x] Failed to locate mod.info. Cannot Continue.  Aborting")
            return False

        with open(mod_info, "rb") as f:
            self.read_ue4_string(f)
            map_count = struct.unpack('i', f.read(4))[0]

            for i in range(map_count):
                cur_map = self.read_ue4_string(f)
                if cur_map:
                    self.map_names.append(cur_map)

        return True



def main():
    parser = argparse.ArgumentParser(description="A utility to download ARK Mods via SteamCMD")
    parser.add_argument("--workingdir", default=None, dest="workingdir", help="Game server home directory.  Current Directory is used if this is not provided")
    parser.add_argument("--modids", nargs="+", default=None, dest="modids", help="ID of Mod To Download")
    parser.add_argument("--steamcmd", default=None, dest="steamcmd", help="Path to SteamCMD")
    parser.add_argument("--update", default=None, action="store_true", dest="mod_update", help="Update Existing Mods.  ")
    parser.add_argument("--preserve", default=None, action="store_true", dest="preserve", help="Don't Delete StreamCMD Content Between Runs")
    parser.add_argument("--namefile", default=None, action="store_true", dest="modname", help="Create a .name File With Mods Text Name")

    args = parser.parse_args()

    if not args.modids and not args.mod_update:
        print("[x] No Mod ID Provided and Update Not Selected.  Aborting")
        print("[?] Please provide a Mod ID to download or use --update to update your existing mods")
        sys.exit(0)

    ArkModDownloader(args.steamcmd,
                     args.modids,
                     args.workingdir,
                     args.mod_update,
                     args.modname,
                     args.preserve)



if __name__ == '__main__':
    main()
