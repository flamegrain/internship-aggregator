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
      setMessage('请输入有效的邮箱地址（如 yourname@university.edu）');
      return;
    }

    setLoading(true);
    setStatus(null);
    setMessage(null);

    try {
      const response = await axios.post(`${apiUrl}/subscribe`, { email });
      setStatus('success');
      setMessage(response.data.message || `订阅成功！最新 20 条实习精选已发送至 ${email}`);
      setEmail('');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setMessage(err.response?.data?.detail || '订阅失败，请检查网络或稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto my-12 px-4">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white p-6 sm:p-10 shadow-xl border border-blue-800/40">
        {/* Glow decoration */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-64 h-64 bg-blue-500/20 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-600/30 border border-blue-500/50 flex items-center justify-center text-blue-400">
                <Bell className="w-6 h-6" />
              </div>
              <div>
                <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-400 bg-blue-950/80 px-2.5 py-0.5 rounded-full border border-blue-800 mb-1">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  最新实习自动速递 • 0 垃圾邮件
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                  订阅全美最新实习速递
                </h3>
              </div>
            </div>

            {/* Preview Email Digest Button */}
            <button
              type="button"
              onClick={() => setShowPreview(true)}
              className="inline-flex items-center gap-1.5 text-xs font-medium bg-slate-800/80 hover:bg-slate-700/80 text-blue-300 border border-slate-700 px-3.5 py-2 rounded-xl transition-all self-start sm:self-center cursor-pointer shadow-xs"
            >
              <Eye className="w-4 h-4" />
              <span>预览 20 条岗位邮件模板</span>
            </button>
          </div>

          <p className="text-sm text-slate-300 max-w-2xl mb-6">
            输入您的邮箱，系统将立即为您推送当前最新的 <strong className="text-white font-semibold">20 条全美精选实习机会</strong>（包含公司类型、时薪待遇、国际生 Visa 支持指数与直达申请链接）。
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 pointer-events-none" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="输入您的学生邮箱 (例如: name@berkeley.edu)"
                className="w-full pl-12 pr-4 py-3.5 rounded-xl bg-slate-800/90 border border-slate-700 text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm sm:text-base"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shrink-0 text-sm sm:text-base"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>推送中...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>立即订阅并获取 20 条</span>
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
              <div className="flex-1 font-medium">{message}</div>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Preview Email Template */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h4 className="text-base font-bold text-slate-900 dark:text-white">
                  邮件速递预览 (Top 20 Postings Email Digest)
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setShowPreview(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
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
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-sm font-medium transition-colors cursor-pointer"
              >
                关闭预览
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailSubscription;
