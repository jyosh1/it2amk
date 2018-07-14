using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;
using System.IO;
using System.Threading;

using G = IT2AMK.Global;
using static IT2AMK.Util.Util;

namespace IT2AMK.Conv
{
	class Converter
	{
		public static Config config = new Config
		{
			use_snesbrr = false,
			force_l0 = false,
			resampler = new CubicResampler()
		};

		public static IT.Sample sample_to_brr(IT.Sample sample, int sample_id, string song_name)
		{
			sample.trim();
			sample.expand_ping_loop();

			if (sample.length % 16 != 0 || sample.loop_start % 16 != 0)
				sample = config.resampler.resample(sample, sample.length);	// Attempt to resample it to same length;
																			// resampler will figure out how to achieve
																			// nearest multiple of 16 loops/length

			string wav_file = G.TEMP_PATH + sample_id.ToString().PadLeft(2, '0') + ".wav";
			string brr_file = G.TEMP_PATH + sample_id.ToString().PadLeft(2, '0') + ".brr";
			string out_file = G.AMK_SAMPLES_PATH + song_name + "/" + sample_id.ToString().PadLeft(2, '0') + " " + format_filename(sample.name) + ".brr";

			sample.save_to_file(wav_file);
			show_verbose("Converting sample {0} to BRR...", sample_id);
			_run_brr_converter(wav_file, brr_file, sample.loop_start);
			if (!_poll_for_file(brr_file, _calculate_brr_size(sample)))
				throw new FileLoadException("The temp file: \"" + brr_file + "\" was incorrectly generated or missing.");
			_fix_brr_loop(sample, brr_file, out_file);

			return sample;
		}

		private static void _run_brr_converter(string wav_file, string brr_file, int loop_point)
		{
			Process proc = new Process();
			proc.StartInfo.WorkingDirectory = "";
			proc.StartInfo.CreateNoWindow = true;
			proc.StartInfo.UseShellExecute = false;

			// For now, force samui
			int loop_arg = (config.force_l0) ? 0 : loop_point;
			//proc.StartInfo.FileName = "Samui.exe";
			//proc.StartInfo.Arguments = string.Format("{0} {1} -l {2}", wav_file, brr_file, loop_arg);
			proc.StartInfo.FileName = "brr_encoder.exe";
			proc.StartInfo.Arguments = string.Format("-l{0} {1} {2}", loop_point, wav_file, brr_file);

			/*if (config.use_snesbrr) {
				int loop_arg = (config.force_l0) ? 0 : loop_point;
				proc.StartInfo.FileName = "snesbrr.exe";
				proc.StartInfo.Arguments = string.Format("-e {0} {1} -l {2}", wav_file, brr_file, loop_arg);
			} else {
				proc.StartInfo.FileName = "brr_encoder.exe";
				proc.StartInfo.Arguments = string.Format("-l{0} {1} {2}", loop_point, wav_file, brr_file);
			}*/

			proc.Start();
			proc.WaitForExit();
		}

		private static bool _poll_for_file(string brr_file, int predicted_size)
		{
			//show_verbose("BRR size: {0} bytes", predicted_size);

			bool file_exists = false;
			for (int i = 0; i < 5; i++) {
				if (File.Exists(brr_file) && new FileInfo(brr_file).Length >= predicted_size) {
					file_exists = true;
					break;
				}
				Thread.Sleep(16);
			}
			return file_exists;
		}

		private static int _calculate_brr_size(IT.Sample sample)
		{
			//show_debug("{0} {1}", sample.loop_start, sample.length);

			Debug.Assert(sample.length % 16 == 0);
			if (sample.looped) {
				Debug.Assert(sample.loop_start % 16 == 0);
				Debug.Assert(sample.loop_end == sample.length);
			}

			if (_initial_block_needed(sample))
				return (config.use_snesbrr) ? 9*sample.length / 16 : 9*sample.length / 16 + 9;
			else
				return 9*sample.length / 16;
		}

		private static void _fix_brr_loop(IT.Sample sample, string brr_file, string new_filename)
		{
			var bytes = new List<byte>();
			byte[] brr_bytes = File.ReadAllBytes(brr_file);

			if (sample.looped) {
				int loop_ptr = 9*sample.loop_start / 16;
				if (!config.use_snesbrr && _initial_block_needed(sample))
					loop_ptr += 9;
				
				append_bytes(bytes, to_bytes((ushort)(loop_ptr)));

				for (int i = 0; i < brr_bytes.Length; i++)
					bytes.Add(brr_bytes[i]);
			} else {
				append_bytes(bytes, to_bytes((ushort)0));

				for (int i = 0; i < brr_bytes.Length; i++) {
					if (i == brr_bytes.Length - 9)
						bytes.Add((byte)(brr_bytes[i] & 0xFD));
					else
						bytes.Add(brr_bytes[i]);
				}
			}

			File.WriteAllBytes(new_filename, bytes.ToArray());
		}

		private static bool _initial_block_needed(IT.Sample sample)
		{
			bool initial_block = false;
			for (int i = 0; i < 16; i++)
				initial_block |= sample.sample_data[i].mono != 0;
			return initial_block;
		}
	}

	struct Config
	{
		public bool use_snesbrr;
		public bool force_l0;
		public Resampler resampler;
	}
}
