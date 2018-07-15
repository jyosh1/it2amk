using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;
using System.IO;

using static IT2AMK.Util.Util;

namespace IT2AMK.IT
{
	enum VIT { Sine, Triangle, Square, Random };

	class Sample
	{
		private List<SamplePoint> _sample_data = new List<SamplePoint>();

		private int _loop_start;
		private int _loop_end;
		private int _sus_loop_start;
		private int _sus_loop_end;

		public string name {get; private set;}
		public string filename {get; private set;}

		public int global_volume {get; private set;}
		public int default_volume {get; private set;}
		public int default_panning {get; private set;}
		public bool use_default_pan {get; private set;}

		public bool has_sample {get; private set;}
		public bool looped {get; private set;}
		public bool sus_looped {get; private set;}
		public bool ping_looped {get; private set;}
		public bool ping_sus_looped {get; private set;}
		
		public int c5_speed {get; set;}

		public int vibrato_speed {get; private set;}
		public int vibrato_depth {get; private set;}
		public VIT vibrato_type {get; private set;}
		public int vibrato_rate {get; private set;}

		public ReadOnlyCollection<SamplePoint> sample_data { get { return _sample_data.AsReadOnly(); } }

		public int loop_start
		{
			get { return _loop_start; }
			set {
				_loop_start = clamp(value, 0, sample_data.Count);
				if (_loop_start > _loop_end)
					_loop_end = _loop_start;
			}
		}
		public int loop_end
		{
			get { return _loop_end; }
			set {
				_loop_end = clamp(value, 0, sample_data.Count);
				if (_loop_start > _loop_end)
					_loop_start = _loop_end;
			}
		}
		public int sus_loop_start
		{
			get { return _sus_loop_start; }
			set {
				_sus_loop_start = clamp(value, 0, sample_data.Count);
				if (_sus_loop_start > _sus_loop_end)
					_sus_loop_end = _sus_loop_start;
			}
		}
		public int sus_loop_end
		{
			get { return _sus_loop_end; }
			set {
				_sus_loop_end = clamp(value, 0, sample_data.Count);
				if (_sus_loop_start > _sus_loop_end)
					_sus_loop_start = _sus_loop_end;
			}
		}
		public int length
		{
			get { return sample_data.Count; }
		}

		public Sample()
		{
		}

		public Sample(Sample s)
		{
			for (int i = 0; i < s._sample_data.Count; i++) {
				_sample_data.Add(s._sample_data[i]);
			}
			name = s.name;
			filename = s.filename;

			global_volume = s.global_volume;
			default_volume = s.default_volume;
			default_panning = s.default_panning;
			use_default_pan = s.use_default_pan;

			has_sample = s.has_sample;
			looped = s.looped;
			sus_looped = s.sus_looped;
			ping_looped = s.ping_looped;
			ping_sus_looped = s.ping_sus_looped;

			_loop_start = s._loop_start;
			_loop_end = s._loop_end;
			c5_speed = s.c5_speed;
			_sus_loop_start = s._sus_loop_start;
			_sus_loop_end = s._sus_loop_end;

			vibrato_speed = s.vibrato_speed;
			vibrato_depth = s.vibrato_depth;
			vibrato_type = s.vibrato_type;
			vibrato_rate = s.vibrato_rate;
		}

		public Sample(byte[] data, int offset, int sample_count)
		{
			load(data, offset, sample_count);
		}

		public void load(byte[] data, int offset, int sample_count)
		{
			try {
				show_verbose("Loading sample {0}...", sample_count + 1);

				if (to_string(data, offset, 4) != "IMPS") {
					throw new InvalidFileException("This is not a valid IT module file. (Incorrect sample header.)");
				}

				_load_metadata(data, offset);
				SampleInfo sp = _load_flags(data, offset);
				_load_mixing_info(data, offset);
				_load_loop_info(data, offset);
				_load_vibrato_info(data, offset);

				if (!has_sample)
					return;

				if (sp.stereo) {
					show_warning("Sample {0} ({1}) is a stereo sample. It will be changed to mono for conversion.",
								 sample_count + 1, name);
				}

				if (sus_looped) {
					show_warning("Sample {0} ({1}) has a sustain loop. It will be ignored.",
								 sample_count + 1, name);
				}

				int length = to_int32(data, offset + 0x30);
				_load_sample_data(data, to_int32(data, offset + 0x48), length, sp.is_16bit, sp.stereo, sp.signed);

			} catch (ArgumentOutOfRangeException) {
				throw new InvalidFileException("This is not a valid IT module file (Out of range error).");
			} catch (IndexOutOfRangeException) {
				throw new InvalidFileException("This is not a valid IT module file (Out of range error).");
			}
		}

		public void save_to_file(string filename)
		{
			try {
				if (filename.EndsWith(".wav"))
					File.WriteAllBytes(filename, save_to_wav_buffer());
				else
					File.WriteAllBytes(filename, save_to_buffer());
			} catch (FileLoadException) {
				throw new FileLoadException("The file: \"" + filename + "\" could not be written to.");
			}
		}

		public byte[] save_to_buffer()
		{
			trim();
			fix_clipping();
			//pad_unlooped();

			var bytes = new List<byte>();

			append_bytes(bytes, Encoding.UTF8.GetBytes("IMPS"));
			append_bytes(bytes, Encoding.UTF8.GetBytes(filename.Substring(0, min(12, filename.Length)).PadRight(12, '\0')));
			bytes.Add(0x00);
			bytes.Add((byte)global_volume);
			int flags = ((looped ? 1 : 0) << 4) + ((sus_looped ? 1 : 0) << 5) + ((ping_looped ? 1 : 0) << 6)
					  + ((ping_sus_looped ? 1 : 0) << 7);
			bytes.Add((byte)(flags | 0x07));
			bytes.Add((byte)default_volume);
			append_bytes(bytes, Encoding.UTF8.GetBytes(name.Substring(0, min(12, name.Length)).PadRight(26, '\0')));
			bytes.Add(1);
			bytes.Add((byte)(default_panning | (use_default_pan ? 0x80 : 0)));
			append_bytes(bytes, to_bytes(sample_data.Count));
			append_bytes(bytes, to_bytes(loop_start));
			append_bytes(bytes, to_bytes(loop_end));
			append_bytes(bytes, to_bytes(c5_speed));
			append_bytes(bytes, to_bytes(sus_loop_start));
			append_bytes(bytes, to_bytes(sus_loop_end));
			append_bytes(bytes, to_bytes(0x50));
			bytes.Add((byte)vibrato_speed);
			bytes.Add((byte)vibrato_depth);
			bytes.Add((byte)vibrato_rate);
			bytes.Add((byte)vibrato_type);

			for (int i = 0; i < sample_data.Count; i++)
				append_bytes(bytes, to_bytes((short)sample_data[i].left));
			for (int i = 0; i < sample_data.Count; i++)
				append_bytes(bytes, to_bytes((short)sample_data[i].right));

			return bytes.ToArray();
		}

		public byte[] save_to_wav_buffer()
		{
			trim();
			fix_clipping();
			//pad_unlooped();

			var bytes = new List<byte>();

			append_bytes(bytes, Encoding.UTF8.GetBytes("RIFF"));
			append_bytes(bytes, to_bytes(36 + 2*length));
			append_bytes(bytes, Encoding.UTF8.GetBytes("WAVEfmt "));
			append_bytes(bytes, to_bytes(16));
			append_bytes(bytes, to_bytes((ushort)1));
			append_bytes(bytes, to_bytes((ushort)1));
			append_bytes(bytes, to_bytes(c5_speed));
			append_bytes(bytes, to_bytes(2*c5_speed));
			append_bytes(bytes, to_bytes((ushort)2));
			append_bytes(bytes, to_bytes((ushort)16));
			append_bytes(bytes, Encoding.UTF8.GetBytes("data"));
			append_bytes(bytes, to_bytes(2*length));

			for (int i = 0; i < length; i++)
				append_bytes(bytes, to_bytes((short)sample_data[i].mono));

			return bytes.ToArray();
		}

		public void clear_sample_data()
		{
			_sample_data.Clear();
			_loop_start = 0;
			_loop_end = 0;
			_sus_loop_start = 0;
			_sus_loop_end = 0;
		}

		public void add_sample_point(SamplePoint sp)
		{
			_sample_data.Add(sp);
		}

		public void trim()
		{
			if (looped) {
				Debug.Assert(loop_end <= _sample_data.Count);

				while (_sample_data.Count > loop_end) {
					_sample_data.RemoveAt(_sample_data.Count - 1);
				}
			}
		}

		public void expand_ping_loop()
		{
			if (ping_looped) {
				trim();

				ping_looped = false;
				for (int i = loop_end - 2; i > loop_start; i--)
					add_sample_point(sample_data[i]);
				_loop_end = length;
			}
		}

		public void fix_clipping()
		{
			int maxh = 0x7FFF;
			for (int i = 0; i < sample_data.Count; i++) {
				var sp = sample_data[i];
				int maxv = max(Math.Abs(sp.left), Math.Abs(sp.right));
				if (maxv > maxh)
					maxh = maxv;
			}

			if (maxh > 0x7FFF) {
				double a = 0x7FFF / (double)maxh;
				for (int i = 0; i < sample_data.Count; i++)
					_sample_data[i] *= a;
			}
		}

		public void amplify(double ratio)
		{
			for (int i = 0; i < sample_data.Count; i++)
				_sample_data[i] *= ratio;
		}

		public void pad_unlooped()
		{
			if (!looped) {
				looped = true;
				_loop_start = length;
				for (int i = 0; i < 16; i++)
					add_sample_point(new SamplePoint(0, 0));
				_loop_end = length;
			}
		}

		public void pad_left()
		{
			// Pad with 0s at the beginning until total length%16==0
			if (length % 16 != 0) {
				int old_length = length;
				int new_length = length + 16 - length%16;
				for (int i = old_length; i < new_length; i++)
					add_sample_point(new SamplePoint(0, 0));
				for (int i = new_length - 1; i >= new_length - old_length; i--)
					_sample_data[i] = _sample_data[i - (new_length - old_length)];
				for (int i = 0; i < new_length - old_length; i++)
					_sample_data[i] = new SamplePoint(0, 0);
				
				//show_debug("{0}", _loop_start);
				loop_end = new_length;
				loop_start += new_length - old_length;

				//show_debug("{0} {1} {2} {3} {4}", old_length, new_length, length, loop_start, loop_end);
			}
		}

		private void _load_metadata(byte[] data, int offset)
		{
			filename = to_string(data, offset + 4, 12);
			name = to_string(data, offset + 0x14, 26);
		}

		private SampleInfo _load_flags(byte[] data, int offset)
		{
			int f = data[offset + 0x12];

			var sp = new SampleInfo {
				flags = f,
				is_16bit = (f & 0x2) > 0,
				stereo = (f & 0x4) > 0,
				compressed = (f & 0x8) > 0,
				signed = (data[offset + 0x2E] & 0x1) > 0
			};

			has_sample = (sp.flags & 0x1) > 0;
			looped = (sp.flags & 0x10) > 0;
			sus_looped = (sp.flags & 0x20) > 0;
			ping_looped = (sp.flags & 0x40) > 0;
			ping_sus_looped = (sp.flags & 0x80) > 0;

			if (sp.compressed) {
				throw new UnsupportedFeatureException("This module contains compressed samples, which are not " +
														"supported in this version.");
			}

			return sp;
		}

		private void _load_mixing_info(byte[] data, int offset)
		{
			global_volume = data[offset + 0x11];
			default_volume = data[offset + 0x13];
			int panning = data[offset + 0x2F];
			default_panning = panning & 0x7F;
			use_default_pan = (panning & 0x80) > 1;
		}

		private void _load_loop_info(byte[] data, int offset)
		{
			_loop_start = to_int32(data, offset + 0x34);
			_loop_end = to_int32(data, offset + 0x38);
			c5_speed = to_int32(data, offset + 0x3C);
			_sus_loop_start = to_int32(data, offset + 0x40);
			_sus_loop_end = to_int32(data, offset + 0x44);
		}

		private void _load_vibrato_info(byte[] data, int offset)
		{
			vibrato_speed = data[offset + 0x4C];
			vibrato_depth = data[offset + 0x4D];
			vibrato_rate = data[offset + 0x4E];
			vibrato_type = (VIT)data[offset + 0x4F];
		}

		private void _load_sample_data(byte[] data, int offset, int length, bool is_16bit, bool stereo, bool signed)
		{
			if (stereo) {
				for (int i = 0; i < length; i++)
					_sample_data.Add(new SamplePoint(_get_sample_point(data, offset, i, length, 0, is_16bit, signed),
													 _get_sample_point(data, offset, i, length, 1, is_16bit, signed)));
			} else {
				for (int i = 0; i < length; i++)
					_sample_data.Add(new SamplePoint(_get_sample_point(data, offset, i, length, 0, is_16bit, signed)));
			}
		}

		private int _get_sample_point(byte[] data, int offset, int index, int length, int c, bool is_16bit, bool signed)
		{
			if (is_16bit) {
				return signed ? to_int16(data, offset + 2*(index + c*length))
								: to_uint16(data, offset + 2*(index + c*length)) - 0x8000;
			} else {
				return 0x100 * (signed ? to_sbyte(data[offset + index + c*length])
										 : data[offset + index + c*length] - 0x80);
			}
		}
	}

	struct SampleInfo
	{
		public int flags;
		public bool is_16bit;
		public bool stereo;
		public bool compressed;
		public bool signed;
	};

	struct SamplePoint
	{
		public int left;
		public int right;

		public int mono
		{
			get {
				return (left + right) / 2;
			}
			set {
				left = value;
				right = value;
			}
		}

		public SamplePoint(int left, int right)
		{
			this.left = left;
			this.right = right;
		}

		public SamplePoint(int mono)
		{
			left = mono;
			right = mono;
		}

		public static SamplePoint operator * (SamplePoint sp, double a)
		{
			return new SamplePoint((int)Math.Floor(a*sp.left + 0.5), (int)Math.Floor(a*sp.right + 0.5));
		}

		public static SamplePoint operator / (SamplePoint sp, double a)
		{
			return new SamplePoint((int)Math.Floor(sp.left/a + 0.5), (int)Math.Floor(sp.right/a + 0.5));
		}

		public static SamplePoint operator + (SamplePoint sp, SamplePoint sp2)
		{
			return new SamplePoint(sp.left + sp2.left, sp.right + sp2.right);
		}
	}
}
