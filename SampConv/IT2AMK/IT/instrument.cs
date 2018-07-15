using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace IT2AMK.IT
{
	enum NNA { Cut, Continue, NoteOff, NoteFade };
	enum DCT { Off, Note, Sample, Instrument };
	enum DCA { Cut, NoteOff, NodeFade };

	class Instrument
	{
		private List<Key> _key_table = new List<Key>();
		private List<Envelope> _envelopes = new List<Envelope>();

		public string name {get; private set;}
		public string filename {get; private set;}

		public NNA new_note_action {get; private set;}
		public DCT dupl_check_type {get; private set;}
		public DCA dupl_check_action {get; private set;}

		public int fadeout {get; private set;}
		public int pitch_pan_sep {get; private set;}
		public Note pitch_pan_center {get; private set;}

		public int global_volume {get; private set;}
		public int default_panning {get; private set;}
		public bool use_default_pan {get; private set;}
		public int random_volume {get; private set;}
		public int random_panning {get; private set;}

		public ReadOnlyCollection<Key> key_table { get { return _key_table.AsReadOnly(); } }
		public ReadOnlyCollection<Envelope> envelopes { get { return _envelopes.AsReadOnly(); } }

		public Instrument()
		{
		}

		public Instrument(byte[] data, int offset)
		{
			load(data, offset);
		}

		public void load(byte[] data, int offset)
		{
		}
	}

	struct Key
	{
		public int sample;
		public Note note;

		public Key(int sample, Note note)
		{
			this.sample = sample;
			this.note = note;
		}
	}
}
