
**Use this at your own risk**

# Goal

I was inspired by [this video from Liveoverflow](https://www.youtube.com/watch?v=UeAKTjx_eKA) to write my own tool on Windows to create copies of USB-sticks. If you are seriously looking for a tool that has this functionality I suggest using `dd` that comes installed with [git for Windows](https://git-scm.com/download/win).

# Basic usage

The script is interactive. It will ask you which usb drive to copy.

![Demonstrate basic interactive usage](quickdd.gif)

# Lessons learned

When trying to copy a physical drive you need to know the size of the disk and the sector size. My first attempts to retrieve the disk size was using the functions available in Python to handle binary files.

## seek

So I tried to use the seek function to give me the address of the last byte.

    with open(r"\\.\PHYSICALDRIVE1", 'rb') as file_handle:
        end_of_file = file_handle.seek(0, 2)
        print(end_of_file)

This piece of code results in `IOError: [Errno 22] Invalid argument`. This is despite the seek function being able to perfectly handle other arguments. You simply cannot call it with `2` as the second parameter.

## fseek

After returning to the Python documentation I learned about `os.open()` and `os.fseek()` which are variants of functions `open()` and `seek()` but more meant for lower level. To quote the documentation on `os.open()`.

> This function is intended for low-level I/O. For normal usage, use the built-in function open(), which returns a file object with read() and write() methods (and many more).

The `os.fseek()` function has exactly the same issue as the `seek()` function. I did switch to using `os.open()` to write the rest of my program.

## Windows Management Instrumentation

After messing around with a few windows utilities I figure that WMI gives me all the information I need. I can list up the drives and retrieve the sector size together with the total amount of sectors.

    PS > wmic diskdrive get DeviceId,TotalSectors,BytesPerSector,Model,InterfaceType
    BytesPerSector  DeviceID            InterfaceType  Model                            TotalSectors
    512             \\.\PHYSICALDRIVE1  USB            Integral Courier USB Device      7823655
    512             \\.\PHYSICALDRIVE0  SCSI           SAMSUNG SSD PM851 2.5 7mm 256GB  500103450

## Unreported sectors

After comparing the images my code produces however I figure that other tools manage to extract more bytes than my tool. It turns out that Windows sometimes lies about the total number of sectors. This is documented on MSDN.

> Note: the value for this property is obtained through extended functions of BIOS interrupt 13h. The value may be inaccurate if the drive uses a translation scheme to support high-capacity disk sizes. Consult the manufacturer for accurate drive specifications.
> https://docs.microsoft.com/en-us/windows/desktop/CIMWin32Prov/win32-diskdrive

There is a [post on Stack Overflow](https://stackoverflow.com/questions/9901792/wmi-win32-diskdrive-to-get-total-sector-on-the-physical-disk-drive#28709238) that also deals with this issue. In short, they advise to try to read beyond the reported sector size until you get a permission error. The Stack Overflow post also mentions issues with buffering. I don't seem to have those and I suspect that this is because I am using `os.open()` instead of `open()`.

I didn't find a more elegant solution. So after my code to read out the reported sectors I added the following code to deal with the unreported sectors.

    unreported = 0
    while True:
        try:
            buffer = os.read(disk_fh, sector_len)
            unreported += 1
            dest_fh.write(buffer)
        except PermissionError:
            break
    print(" `-> %d unreported sectors found" % unreported)

This isn't a pretty solution. At least the checksums and the file size now matches the output of other utilities.

    $ md5sum.exe *.copy
    0b75bdefe54aa20dd061db39d41adcc5 *dd.copy
    0b75bdefe54aa20dd061db39d41adcc5 *IntegralCourierUSBDevice.copy

