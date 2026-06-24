import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useBudgetTimelineQuery } from '../hooks/useBudgetTimelineQuery';
import { formatUzs } from '@/lib/format';
import { ArrowDownRight, ArrowUpRight, Calendar, Clock, CheckCircle } from 'lucide-react';

export function BudgetTimeline({ budgetYear, budgetMonth }) {
    const { t, i18n } = useTranslation();
    const { data: timeline, isLoading, error } = useBudgetTimelineQuery(budgetYear, budgetMonth);

    const groupedEvents = useMemo(() => {
        if (!timeline?.items) return [];
        
        const groups = {};
        for (const event of timeline.items) {
            if (!groups[event.date]) {
                groups[event.date] = [];
            }
            groups[event.date].push(event);
        }

        return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]));
    }, [timeline]);

    if (isLoading) {
        return (
            <div className="p-8 flex flex-col items-center justify-center space-y-4">
                <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-slate-500 text-sm font-medium animate-pulse">{t('common.loading', 'Loading...')}</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 bg-rose-50 rounded-2xl text-center border border-rose-100">
                <p className="text-rose-600 font-medium">{t('common.error', 'Something went wrong')}</p>
            </div>
        );
    }

    if (!timeline?.items?.length) {
        return (
            <div className="p-12 text-center text-slate-500 flex flex-col items-center bg-slate-50/50 rounded-3xl border border-slate-100 border-dashed">
                <div className="w-16 h-16 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-center mb-4">
                    <Calendar className="w-8 h-8 text-slate-300" />
                </div>
                <p className="font-medium text-slate-900 mb-1">{t('budgets.timeline.empty_title', 'No events scheduled')}</p>
                <p className="text-sm">{t('budgets.timeline.empty_subtitle', 'Your timeline is clear for this month.')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {groupedEvents.map(([dateString, events]) => {
                // dateString is YYYY-MM-DD
                const parts = dateString.split('-');
                const y = parseInt(parts[0], 10);
                const m = parseInt(parts[1], 10);
                const d = parseInt(parts[2], 10);
                const dateObj = new Date(y, m - 1, d);
                
                const formatter = new Intl.DateTimeFormat(i18n.language || 'en-US', { weekday: 'long' });
                const weekdayName = formatter.format(dateObj);
                
                const monthFormatter = new Intl.DateTimeFormat(i18n.language || 'en-US', { month: 'short' });
                const monthName = monthFormatter.format(dateObj);

                // Calculate net for the day
                const netDay = events.reduce((acc, ev) => {
                    return acc + (ev.direction === 'INFLOW' ? ev.amount : -ev.amount);
                }, 0);

                return (
                    <div key={dateString} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300 hover:shadow-md hover:border-slate-300">
                        {/* Day Header */}
                        <div className="bg-slate-50/80 px-5 py-4 border-b border-slate-100 flex justify-between items-center backdrop-blur-sm">
                            <div className="flex items-center gap-4">
                                <div className="bg-white shadow-sm border border-slate-200 text-slate-700 w-14 h-14 rounded-xl flex flex-col items-center justify-center font-bold transform transition-transform hover:scale-105">
                                    <span className="text-[10px] uppercase tracking-wider text-slate-500 mb-0.5">{monthName}</span>
                                    <span className="text-xl leading-none text-slate-900">{d}</span>
                                </div>
                                <div>
                                    <h4 className="font-semibold text-slate-900 text-base capitalize">{weekdayName}</h4>
                                    <p className="text-xs text-slate-500 font-medium">{events.length} {events.length === 1 ? t('common.event', 'event') : t('common.events', 'events')}</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">{t('budgets.timeline.daily_net', 'Daily Net')}</div>
                                <div className={`font-bold text-sm px-2.5 py-1 rounded-full inline-block ${netDay > 0 ? 'bg-emerald-50 text-emerald-700' : netDay < 0 ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-700'}`}>
                                    {netDay > 0 ? '+' : ''}{formatUzs(Math.abs(netDay))}
                                </div>
                            </div>
                        </div>

                        {/* Events List */}
                        <div className="divide-y divide-slate-100">
                            {events.map((event) => (
                                <div key={event.id} className="p-5 flex items-center justify-between hover:bg-slate-50/50 transition-colors group">
                                    <div className="flex items-center gap-4">
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center transform transition-transform group-hover:scale-110 shadow-sm ${
                                            event.direction === 'INFLOW' 
                                                ? 'bg-emerald-100 text-emerald-600 border border-emerald-200' 
                                                : 'bg-rose-100 text-rose-600 border border-rose-200'
                                        }`}>
                                            {event.direction === 'INFLOW' ? <ArrowDownRight size={18} strokeWidth={2.5} /> : <ArrowUpRight size={18} strokeWidth={2.5} />}
                                        </div>
                                        <div>
                                            <div className="font-semibold text-slate-900 mb-0.5">{event.title}</div>
                                            <div className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5 uppercase tracking-wide">
                                                {event.status === 'PENDING' ? <Clock size={12} className="text-amber-500" /> : <CheckCircle size={12} className="text-emerald-500" />}
                                                <span>{event.event_type.replace('_', ' ')}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className={`font-bold text-base ${event.direction === 'INFLOW' ? 'text-emerald-600' : 'text-slate-900'}`}>
                                        {event.direction === 'INFLOW' ? '+' : '-'}{formatUzs(event.amount)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
