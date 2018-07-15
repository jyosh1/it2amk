using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using System.IO.Compression;

namespace IT2AMK.Util
{
	class Util
	{
		public static bool warnings_enabled = true;
		public static bool verbose_enabled = false;
		public static bool messages_enabled = true;
		public static bool debug_enabled = false;

		public static int hex_to_int(string hexstr)
		{
			return int.Parse(hexstr, System.Globalization.NumberStyles.HexNumber);
		}

		public static int hex_to_int(char hexchr)
		{
			return int.Parse(hexchr.ToString(), System.Globalization.NumberStyles.HexNumber);
		}

		public static string int_to_hex(int num, uint digitcount=2)
		{
			return num.ToString("X" + digitcount.ToString());
		}

		public static int min(params int[] fs)
		{
			int r = fs[0];
			for (int i = 1; i < fs.Length; i++) {
				if (fs[i] < r)
					r = fs[i];
			}
			return r;
		}

		public static int max(params int[] fs)
		{
			int r = fs[0];
			for (int i = 1; i < fs.Length; i++) {
				if (fs[i] > r)
					r = fs[i];
			}
			return r;
		}

		public static int clamp(int source, int lower, int higher)
		{
			return max(min(source, higher), lower);
		}

		public static double min(params double[] fs)
		{
			double r = fs[0];
			for (int i = 1; i < fs.Length; i++) {
				if (fs[i] < r)
					r = fs[i];
			}
			return r;
		}

		public static double max(params double[] fs)
		{
			double r = fs[0];
			for (int i = 1; i < fs.Length; i++) {
				if (fs[i] > r)
					r = fs[i];
			}
			return r;
		}

		public static double clamp(double source, double lower, double higher)
		{
			return max(min(source, higher), lower);
		}

		public static double sinc(double x)
		{
			if (x == 0)
				return 1;
			else
				return Math.Sin(Math.PI * x) / (Math.PI * x);
		}

		public static double round(double x)
		{
			return Math.Floor(x + 0.5);
		}

		public static int iround(double x)
		{
			return (int)round(x);
		}

		public static int ifloor(double x)
		{
			return (int)Math.Floor(x);
		}

		/*public static byte[] compress(byte[] data)
		{
			MemoryStream output = new MemoryStream();
			using (DeflateStream dstream = new DeflateStream(output, CompressionLevel.Optimal))
			{
				dstream.Write(data, 0, data.Length);
			}
			return output.ToArray();
		}

		public static byte[] decompress(byte[] data)
		{
			MemoryStream input = new MemoryStream(data);
			MemoryStream output = new MemoryStream();
			using (DeflateStream dstream = new DeflateStream(input, CompressionMode.Decompress))
			{
				dstream.CopyTo(output);
			}
			return output.ToArray();
		}*/

		public static sbyte to_sbyte(byte value)
		{
			return unchecked((sbyte)value);
		}

		public static Int16 to_int16(byte[] bytes, int start_index)
		{
			if (!BitConverter.IsLittleEndian) {
				Array.Reverse(bytes);
				start_index = bytes.Length - start_index - 2;
			}
			return BitConverter.ToInt16(bytes, start_index);
		}

		public static UInt16 to_uint16(byte[] bytes, int start_index)
		{
			if (!BitConverter.IsLittleEndian) {
				Array.Reverse(bytes);
				start_index = bytes.Length - start_index - 2;
			}
			return BitConverter.ToUInt16(bytes, start_index);
		}

		public static Int32 to_int32(byte[] bytes, int start_index)
		{
			if (!BitConverter.IsLittleEndian) {
				Array.Reverse(bytes);
				start_index = bytes.Length - start_index - 4;
			}
			return BitConverter.ToInt32(bytes, start_index);
		}

		public static UInt32 to_uint32(byte[] bytes, int start_index)
		{
			if (!BitConverter.IsLittleEndian) {
				Array.Reverse(bytes);
				start_index = bytes.Length - start_index - 4;
			}
			return BitConverter.ToUInt32(bytes, start_index);
		}

		public static Int64 to_int64(byte[] bytes, int start_index)
		{
			if (!BitConverter.IsLittleEndian) {
				Array.Reverse(bytes);
				start_index = bytes.Length - start_index - 8;
			}
			return BitConverter.ToInt64(bytes, start_index);
		}

		public static UInt64 to_uint64(byte[] bytes, int start_index)
		{
			if (!BitConverter.IsLittleEndian) {
				Array.Reverse(bytes);
				start_index = bytes.Length - start_index - 8;
			}
			return BitConverter.ToUInt64(bytes, start_index);
		}

		public static string to_string(byte[] bytes, int start_index, int max_length)
		{
			byte[] subarray = bytes.Skip(start_index).Take(max_length).ToArray();
			return Encoding.UTF8.GetString(subarray).TrimEnd('\0');
		}

		public static byte to_byte(sbyte value)
		{
			sbyte[] signed = {value};
			byte[] unsigned = (byte[])(Array)signed;
			return unsigned[0];
		}

		public static byte[] to_bytes(short value, bool big_endian=false)
		{
			byte[] bytes = BitConverter.GetBytes(value);
			if (big_endian)
				Array.Reverse(bytes);
			return bytes;
		}

		public static byte[] to_bytes(ushort value, bool big_endian=false)
		{
			byte[] bytes = BitConverter.GetBytes(value);
			if (big_endian)
				Array.Reverse(bytes);
			return bytes;
		}

		public static byte[] to_bytes(int value, bool big_endian=false)
		{
			byte[] bytes = BitConverter.GetBytes(value);
			if (big_endian)
				Array.Reverse(bytes);
			return bytes;
		}

		public static byte[] to_bytes(uint value, bool big_endian=false)
		{
			byte[] bytes = BitConverter.GetBytes(value);
			if (big_endian)
				Array.Reverse(bytes);
			return bytes;
		}

		public static byte[] to_bytes(long value, bool big_endian=false)
		{
			byte[] bytes = BitConverter.GetBytes(value);
			if (big_endian)
				Array.Reverse(bytes);
			return bytes;
		}

		public static byte[] to_bytes(ulong value, bool big_endian=false)
		{
			byte[] bytes = BitConverter.GetBytes(value);
			if (big_endian)
				Array.Reverse(bytes);
			return bytes;
		}

		public static void append_bytes(List<byte> list, byte[] bytes)
		{
			for (int i = 0; i < bytes.Length; i++) {
				list.Add(bytes[i]);
			}
		}

		public static void show_debug(params object[] list)
		{
			if (debug_enabled)
				Console.WriteLine(string.Format("" + list[0], list.Skip(1).Take(list.Length - 1).ToArray()));
		}

		public static void show_message(params object[] list)
		{
			if (messages_enabled)
				Console.WriteLine(string.Format("" + list[0], list.Skip(1).Take(list.Length - 1).ToArray()));
		}

		public static void show_verbose(params object[] list)
		{
			if (verbose_enabled)
				Console.WriteLine(string.Format("- " + list[0] + " -", list.Skip(1).Take(list.Length - 1).ToArray()));
		}

		public static void show_warning(params object[] list)
		{
			if (warnings_enabled)
				Console.WriteLine(string.Format("Warning: " + list[0], list.Skip(1).Take(list.Length - 1).ToArray()));
		}

		public static void show_error(params object[] list)
		{
			Console.WriteLine(string.Format("Error: " + list[0], list.Skip(1).Take(list.Length - 1).ToArray()));
		}

		public static void print_list<T>(List<T> list)
		{
			string s = "{ ";
			for (int i = 0; i < list.Count; i++) {
				s += string.Format("{0} ", list[i]);
			}
			Console.WriteLine(s + "}");
		}

		public static string format_filename(string filename)
		{
			string invalid = new string(Path.GetInvalidFileNameChars()) + new string(Path.GetInvalidPathChars());

			foreach (char c in invalid)
				filename = filename.Replace(c.ToString(), ""); 

			return filename;
		}
	}
}
