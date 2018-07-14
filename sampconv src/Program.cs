using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;
using System.IO;

using G = IT2AMK.Global;
using static IT2AMK.Util.Util;

namespace IT2AMK
{
	class Program
	{
		static void Main(string[] args)
		{
			string it_file = "";

			var use_flags = new List<bool>();
			var resample_ratios = new List<double>();
			var amp_ratios = new List<double>();

			if (args.Length < 1) {
				//Console.WriteLine("Usage: {0} <itfile.it> [<arg1> <arg2> ...]\nType {0} --help for more info", "it2amk");
				Console.WriteLine("Usage: {0} <itfile.it>", "it2amk");
				//Environment.Exit(1);
				Console.Write("Enter IT file name: ");
				it_file = Console.ReadLine();
			} else if (args[0] == "--help") {
				Console.WriteLine("List of valid commands:");
				Environment.Exit(0);
			} else {
				it_file = args[0];
				if (args.Length >= 2) {
					for (int i = 0; i < args[1].Length; i++) {
						if (args[1][i] == '1')
							use_flags.Add(true);
						else
							use_flags.Add(false);
					}
				}
				for (int i = 2; i < args.Length; i += 2) {
					resample_ratios.Add(Double.Parse(args[i]));
					if (i + 1 < args.Length)
						amp_ratios.Add(Double.Parse(args[i + 1]));
				}
			}

			Stopwatch stopwatch = Stopwatch.StartNew(); //creates and start the instance of Stopwatch
			bool error = false;

			try {
				verbose_enabled = true;
				debug_enabled = true;

				write_sysinfo();
				clear_temp_folder();

				string folder_name = it_file.Split('.')[0];
				var split_list = folder_name.Replace('\\', '/').Split('/');
				folder_name = split_list[split_list.Length - 1];

				if (!Directory.Exists(G.AMK_SAMPLES_PATH + folder_name)) {
					show_verbose("Creating directory \"{0}\"...", G.AMK_SAMPLES_PATH + folder_name);
					Directory.CreateDirectory(G.AMK_SAMPLES_PATH + folder_name);
				} else {
					show_verbose("Clearing directory \"{0}\"...", G.AMK_SAMPLES_PATH + folder_name);
					clear_folder(G.AMK_SAMPLES_PATH + folder_name);
				}
				
				var it = new IT.Module(it_file);
				IT.Sample prepared;

				string tuning_str = "";

				for (int i = 0; i < it.samples.Count; i++) {
					if (it.samples[i].has_sample && (i >= use_flags.Count || use_flags[i])) {
						it.samples[i].trim();
						it.samples[i].expand_ping_loop();
						//var rs = new Conv.SincResampler(512).resample(it.samples[i], it.samples[i].length/2);
						if (i < amp_ratios.Count) {
							//Console.WriteLine("AMPLIFYING BY {0}", amp_ratios[i]);
							it.samples[i].amplify(amp_ratios[i]);
						}
						if (i < resample_ratios.Count) {
							var rs = new Conv.CubicResampler().resample(it.samples[i], it.samples[i].length * resample_ratios[i]);
							prepared = Conv.Converter.sample_to_brr(rs, i + 1, folder_name);
						} else {
							prepared = Conv.Converter.sample_to_brr(it.samples[i], i + 1, folder_name);
						}

						string fname = (i + 1).ToString().PadLeft(2, '0') + " " + format_filename(prepared.name) + ".brr";
						tuning_str += "\"" + fname + "\" $" + int_to_hex(iround((double)prepared.c5_speed * 768 / 12539), 4) + "\n";
					}
				}

				File.WriteAllText(G.TEMP_PATH + "tunings.txt", tuning_str);

			} catch (FileNotFoundException e) {
				show_error(e.Message);
				error = true;
			} catch (FileLoadException e) {
				show_error(e.Message);
				error = true;
			} catch (IT.InvalidFileException e) {
				show_error(e.Message);
				error = true;
			} catch (IOException e) {
				show_error(e.Message);
				error = true;
			} catch (UnauthorizedAccessException e) {
				show_error(e.Message);
				error = true;
			} catch (ArgumentException e) {
				show_error(e.Message);
				error = true;
			} catch (NotSupportedException e) {
				show_error(e.Message);
				error = true;
			}

			if (!error) {
				stopwatch.Stop();
				//Console.WriteLine("Done! {0} ms", stopwatch.ElapsedMilliseconds);
				//Console.Read();
			} else {
				Environment.Exit(1);
			}
		}

		public static void clear_temp_folder()
		{
			show_verbose("Clearing temporary sample files...");
			clear_folder(G.TEMP_PATH);
		}

		public static void clear_folder(string path)
		{
			DirectoryInfo di = new DirectoryInfo(path);

			foreach (FileInfo file in di.GetFiles()) {
				file.Delete(); 
			}
		}

		public static void write_sysinfo()
		{
			string[] lines = {
				string.Format("{0} {1}", "RAM".PadRight(14, ' '), Util.CPU.get_total_memory()),
				string.Format("{0} {1}", "OS".PadRight(14, ' '), Util.CPU.get_os()),
				string.Format("{0} {1} ({2})", "Processor".PadRight(14, ' '), Util.CPU.get_processor_name(),
							  Util.CPU.get_os_bits()),
				string.Format("{0} {1} ({2})", "Architecture".PadRight(14, ' '), Util.CPU.get_architecture(),
							  Util.CPU.get_endianness())
			};

			File.WriteAllLines("sysinfo.txt", lines);
		}
	}
}
