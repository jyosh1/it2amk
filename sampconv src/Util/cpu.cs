using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.VisualBasic.Devices;

namespace IT2AMK.Util
{
	class CPU
	{
		public static Memory get_total_memory()
		{
			return new Memory
			{
				bytes = new ComputerInfo().TotalPhysicalMemory
			};
		}

		public static string get_os()
		{
			return new ComputerInfo().OSFullName;
		}

		public static string get_os_bits()
		{
			return (Environment.Is64BitOperatingSystem) ? "64-bit" : "32-bit";
		}

		public static string get_processor_name()
		{
			return Environment.GetEnvironmentVariable("PROCESSOR_IDENTIFIER");
		}

		public static string get_architecture()
		{
			return Environment.GetEnvironmentVariable("PROCESSOR_ARCHITECTURE", EnvironmentVariableTarget.Machine);
		}

		public static string get_endianness()
		{
			return (BitConverter.IsLittleEndian) ? "Little Endian" : "Big Endian";
		}
	}

	struct Memory
	{
		public ulong bytes;
		public double kb
		{
			get {
				return Math.Round(bytes / 1024.0, 2);
			}
		}
		public double mb
		{
			get {
				return Math.Round(bytes / Math.Pow(1024, 2), 2);
			}
		}
		public double gb
		{
			get {
				return Math.Round(bytes / Math.Pow(1024, 3), 2);
			}
		}
		public double tb
		{
			get {
				return Math.Round(bytes / Math.Pow(1024, 4), 2);
			}
		}

		public override string ToString()
		{
			if (bytes >= Math.Pow(1024, 4)) {
				return tb.ToString() + " TB";
			} else if (bytes >= Math.Pow(1024, 3)) {
				return gb.ToString() + " GB";
			} else if (bytes >= Math.Pow(1024, 2)) {
				return mb.ToString() + " MB";
			} else if (bytes >= 1024) {
				return gb.ToString() + " KB";
			} else {
				return gb.ToString() + " Bytes";
			}
		}
	}
}
