import React, { useState } from 'react';
import axios from 'axios';
import { Mail, Send, CheckCircle2, AlertCircle, Eye, X, Sparkles, Bell } from 'lucide-react';

const EmailSubscription = ({ apiUrl }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [status, setStatus] = useState(null); // 'success' | 'error' | null
  const [showPreview, setShowPreview] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      setStatus('error');
      setMessage('Please enter a valid email address (e.g. alex@berkeley.edu)');
      return;
    }

    setLoading(true);
    setStatus(null);
    setMessage(null);

    try {
      const response = await axios.post(`${apiUrl}/subscribe`, { email });
      setStatus('success');
      setMessage(response.data.message || `Subscribed! Top 20 freshest internships sent to ${email}`);
      setEmail('');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setMessage(err.response?.data?.detail || 'Subscription failed. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto my-12">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white p-6 sm:p-10 shadow-xl border border-blue-800/50">
        {/* Glow decoration */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-72 h-72 bg-blue-500/20 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-72 h-72 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-600/30 border border-blue-500/50 flex items-center justify-center text-blue-400 shrink-0">
                <Bell className="w-6 h-6" />
              </div>
              <div>
                <div className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-400 bg-blue-950/80 px-2.5 py-0.5 rounded-full border border-blue-800 mb-1">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  Daily Internship Radar • Zero Spam
                </div>
                <h3 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                  Never Miss The Drop: Get Daily Postings
                </h3>
              </div>
            </div>

            {/* Preview Email Digest Button */}
            <button
              type="button"
              onClick={() => setShowPreview(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold bg-slate-800/90 hover:bg-slate-700 text-blue-300 border border-slate-700 px-3.5 py-2.5 rounded-xl transition-all self-start sm:self-center cursor-pointer shadow-sm hover:text-white"
            >
              <Eye className="w-4 h-4" />
              <span>Preview 20-Post Digest</span>
            </button>
          </div>

          <p className="text-sm sm:text-base text-slate-300 max-w-2xl mb-6 leading-relaxed">
            Drop your email below. We'll instantly blast the <strong className="text-white font-bold">20 freshest, highest-paying tech & finance internships</strong> directly to your inbox before they get flooded on LinkedIn.
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 pointer-events-none" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your student email (e.g. student@stanford.edu)"
                className="w-full pl-12 pr-4 py-3.5 rounded-xl bg-slate-800/90 border border-slate-700 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm sm:text-base shadow-inner"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shrink-0 text-sm sm:text-base"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Send Me Top 20 Postings ⚡</span>
                </>
              )}
            </button>
          </form>

          {/* Feedback status message */}
          {message && (
            <div
              className={`mt-4 p-3.5 rounded-xl text-sm flex items-start gap-2.5 ${
                status === 'success'
                  ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                  : 'bg-rose-950/80 text-rose-300 border border-rose-800'
              }`}
            >
              {status === 'success' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              )}
              <div className="flex-1 font-semibold">{message}</div>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Preview Email Template */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h4 className="text-base font-bold text-slate-900 dark:text-white">
                  Top 20 Postings Email Digest Preview
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setShowPreview(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body: Iframe loading preview */}
            <div className="flex-1 overflow-auto p-4 bg-slate-100 dark:bg-slate-950">
              <iframe
                src={`${apiUrl}/subscribe/preview`}
                title="Email Preview"
                className="w-full h-[600px] rounded-xl border border-slate-300 dark:border-slate-700 bg-white"
              />
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex justify-end">
              <button
                type="button"
                onClick={() => setShowPreview(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-sm font-semibold transition-colors cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailSubscription;
