**ARK Mod Downloader**
------------------------------
As many know you cannot simply download ARK mods via SteamCMD.  The individual files come archived as .z files which will not work with a server. 

This tool works around this issue by downloading the mod and extracting the .z files. 

**Usage**

You can either run this tool via the .exe provided in the dist folder or directly via the Ark_Mod_Downloader Python script.

***Commandline Args***

**--workingdir** - (Optional) - This is the home directory of your ARK server

**--modids** - The IDs of the mod you wish to download.  Space separated list of Mod IDs to download

**--steamcmd** - (Optional) - The directory to the SteamCMD exe you wish to use.  If not provided the tool will download SteamCMD to the CWD

**--update** - (Optional) - This will update all current mods installed on the server

**--namefile** - (Optional) - This will create a "Modname.name" file in the mod folder. 

The only required argument is the --modid if you run this script from the root of your Game Server.

**Credits**
<a href="https://github.com/project-umbrella/arkit.py" target="_blank">arkit.py</a> - Used to extract the .z files