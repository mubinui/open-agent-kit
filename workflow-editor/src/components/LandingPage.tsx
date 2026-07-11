import React, { useEffect, useState } from 'react';
import { ArrowRight, Shield, Zap, Layers, RefreshCw, Code2, Rocket, Play, Activity } from 'lucide-react';
import { OakLogo } from './OakLogo';
import { api } from '../api/client';

interface LandingPageProps {
    onEnterStudio: () => void;
    onOpenTester: () => void;
    onOpenDeploy: () => void;
    onOpenAuth: () => void;
}

interface StudioState {
    counts?: { workflows?: number; agents?: number; tools?: number };
}

export const LandingPage: React.FC<LandingPageProps> = ({
    onEnterStudio,
    onOpenTester,
    onOpenDeploy,
    onOpenAuth,
}) => {
    const [backendUp, setBackendUp] = useState<boolean | null>(null);
    const [counts, setCounts] = useState<{ workflows: number; agents: number; tools: number } | null>(null);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                await api('/health');
                if (!cancelled) setBackendUp(true);
                const state = await api<StudioState>('/api/v1/studio/state');
                if (!cancelled && state?.counts) {
                    setCounts({
                        workflows: state.counts.workflows ?? 0,
                        agents: state.counts.agents ?? 0,
                        tools: state.counts.tools ?? 0,
                    });
                }
            } catch {
                if (!cancelled) setBackendUp(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    return (
        <div className="absolute inset-0 bg-[#0b0f19] text-slate-100 overflow-y-auto flex flex-col justify-between z-30 selection:bg-emerald-600 selection:text-white antialiased font-sans">
            {/* Ambient glows */}
            <div className="absolute top-0 left-1/3 w-[600px] h-[600px] bg-gradient-to-br from-emerald-600/15 to-teal-600/5 rounded-full blur-[140px] pointer-events-none transform -translate-x-1/2 -translate-y-1/3"></div>
            <div className="absolute bottom-10 right-1/4 w-[500px] h-[500px] bg-gradient-to-tr from-teal-600/10 to-emerald-600/5 rounded-full blur-[120px] pointer-events-none transform translate-x-1/3"></div>

            {/* Top navigation */}
            <header className="w-full max-w-7xl mx-auto px-8 py-6 flex items-center justify-between relative z-10 border-b border-slate-800/40 bg-[#0b0f19]/60 backdrop-blur-md sticky top-0">
                <div className="flex items-center gap-3.5">
                    <OakLogo className="w-9 h-9 rounded-xl shadow-lg shadow-emerald-500/20" />
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                            <span className="font-extrabold text-sm tracking-tight text-white">Open Agent Kit</span>
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 tracking-wider uppercase">Open Source</span>
                        </div>
                        <span className="text-[11px] text-slate-400 tracking-wide font-medium">Multi-agent development studio</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={onOpenAuth}
                        className="text-xs font-semibold text-slate-300 hover:text-white px-3 py-2 rounded-lg hover:bg-slate-800/60 transition-all"
                    >
                        Account
                    </button>
                    <button
                        onClick={onEnterStudio}
                        className="group flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-white/10 hover:bg-white/20 rounded-lg border border-white/10 transition-all shadow-sm"
                    >
                        <Play className="w-3 h-3 text-emerald-400 fill-emerald-400 group-hover:scale-110 transition-transform" />
                        Enter Studio
                    </button>
                </div>
            </header>

            {/* Main content */}
            <main className="w-full max-w-7xl mx-auto px-8 py-12 flex flex-col justify-center relative z-10 flex-grow">
                {/* Live backend status pill */}
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-slate-800 w-fit mb-8 shadow-inner">
                    <span
                        className={`flex h-2 w-2 rounded-full ${backendUp === null ? 'bg-slate-500' : backendUp ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`}
                    ></span>
                    <span className="text-[11px] font-medium text-slate-300 tracking-wide">
                        {backendUp === null
                            ? 'Checking backend…'
                            : backendUp
                                ? counts
                                    ? `Backend online · ${counts.workflows} workflows · ${counts.agents} agents · ${counts.tools} tools`
                                    : 'Backend online'
                                : 'Backend unreachable — start the API server'}
                    </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                    {/* Headline */}
                    <div className="lg:col-span-7 space-y-6">
                        <h1 className="text-4xl md:text-6xl font-black tracking-tight text-white leading-[1.08]">
                            Build, test, and ship <br />
                            <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-emerald-400 bg-clip-text text-transparent">
                                multi-agent workflows.
                            </span>
                        </h1>

                        <p className="text-slate-300 text-sm md:text-base font-normal max-w-xl leading-relaxed">
                            Open Agent Kit is an open-source studio for CrewAI agents: design workflows on a
                            visual canvas, wire in tools and knowledge, chat with your agents live, and deploy
                            them as standalone chat pages — all from one place.
                        </p>

                        {/* Quick start steps */}
                        <div className="grid grid-cols-3 gap-4 pt-4 pb-2 max-w-lg">
                            <div className="border-l-2 border-emerald-500 pl-3 py-1 bg-gradient-to-r from-emerald-500/5 to-transparent">
                                <div className="text-lg font-bold text-white">1. Design</div>
                                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Drag agents onto the canvas</div>
                            </div>
                            <div className="border-l-2 border-teal-500 pl-3 py-1 bg-gradient-to-r from-teal-500/5 to-transparent">
                                <div className="text-lg font-bold text-white">2. Test</div>
                                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Chat with live LLMs</div>
                            </div>
                            <div className="border-l-2 border-emerald-400 pl-3 py-1 bg-gradient-to-r from-emerald-400/5 to-transparent">
                                <div className="text-lg font-bold text-white">3. Deploy</div>
                                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">One-click chat pages</div>
                            </div>
                        </div>

                        <div className="pt-2 flex flex-wrap items-center gap-4">
                            <button
                                onClick={onEnterStudio}
                                className="flex items-center gap-3 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-sm shadow-xl shadow-emerald-600/20 hover:shadow-emerald-600/30 transition-all hover:-translate-y-0.5"
                            >
                                <Layers className="w-4 h-4" />
                                Open the Studio
                            </button>
                            <a
                                href="/docs"
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs font-semibold text-slate-300 hover:text-white px-3 py-2 rounded-lg hover:bg-slate-800/60 transition-all"
                            >
                                API Reference →
                            </a>
                        </div>
                    </div>

                    {/* Capability cards */}
                    <div className="lg:col-span-5 space-y-4">
                        <div className="text-xs font-bold text-slate-500 tracking-wider uppercase px-1">What's inside</div>

                        <div
                            onClick={onEnterStudio}
                            className="group relative p-5 bg-slate-900/50 hover:bg-slate-900 rounded-xl border border-slate-800/80 hover:border-emerald-500/40 transition-all cursor-pointer flex items-start gap-4 overflow-hidden shadow-sm"
                        >
                            <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg group-hover:bg-emerald-500 group-hover:text-white transition-colors shrink-0">
                                <Layers className="w-5 h-5" />
                            </div>
                            <div className="flex-grow min-w-0">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">Visual Workflow Canvas</h3>
                                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
                                </div>
                                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                                    Compose selector, sequential, and parallel agent topologies with drag-and-drop
                                    nodes. The bundled demo workflow routes between search, RAG, and calculator specialists.
                                </p>
                            </div>
                        </div>

                        <div
                            onClick={onOpenTester}
                            className="group relative p-5 bg-slate-900/50 hover:bg-slate-900 rounded-xl border border-slate-800/80 hover:border-teal-500/40 transition-all cursor-pointer flex items-start gap-4 overflow-hidden shadow-sm"
                        >
                            <div className="absolute top-0 left-0 w-1 h-full bg-teal-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div className="p-3 bg-teal-500/10 text-teal-400 rounded-lg group-hover:bg-teal-500 group-hover:text-white transition-colors shrink-0">
                                <Zap className="w-5 h-5" />
                            </div>
                            <div className="flex-grow min-w-0">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-bold text-white group-hover:text-teal-400 transition-colors">Live LLM Tester</h3>
                                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
                                </div>
                                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                                    Send prompts straight to any LiteLLM-supported model and inspect latency,
                                    token usage, and estimated cost — perfect for validating keys and models.
                                </p>
                            </div>
                        </div>

                        <div
                            onClick={onOpenDeploy}
                            className="group relative p-5 bg-slate-900/50 hover:bg-slate-900 rounded-xl border border-slate-800/80 hover:border-emerald-500/40 transition-all cursor-pointer flex items-start gap-4 overflow-hidden shadow-sm"
                        >
                            <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg group-hover:bg-emerald-500 group-hover:text-white transition-colors shrink-0">
                                <Rocket className="w-5 h-5" />
                            </div>
                            <div className="flex-grow min-w-0">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">Flash Deployments</h3>
                                    <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
                                </div>
                                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                                    Publish any workflow as a standalone chat page served by this app at /d/&lt;name&gt;/ —
                                    embed it anywhere with a single iframe.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Feature strip */}
                <div className="mt-16 pt-8 border-t border-slate-800/60 grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div className="flex items-start gap-3">
                        <Shield className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                        <div>
                            <div className="text-xs font-bold text-slate-200">Guardrails & Validation</div>
                            <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">Response-quality checks and output-format validation built in.</div>
                        </div>
                    </div>
                    <div className="flex items-start gap-3">
                        <RefreshCw className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                        <div>
                            <div className="text-xs font-bold text-slate-200">CrewAI Runtime</div>
                            <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">Workflows execute on CrewAI with selector, sequential, and parallel patterns.</div>
                        </div>
                    </div>
                    <div className="flex items-start gap-3">
                        <Code2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                        <div>
                            <div className="text-xs font-bold text-slate-200">Any LLM via LiteLLM</div>
                            <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">OpenRouter, OpenAI, Gemini, self-hosted vLLM, or local Ollama.</div>
                        </div>
                    </div>
                    <div className="flex items-start gap-3">
                        <Activity className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
                        <div>
                            <div className="text-xs font-bold text-slate-200">Tools & Knowledge</div>
                            <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">Web search, RAG, calculators, and any REST API via Swagger import.</div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="w-full py-5 px-8 border-t border-slate-800/40 text-center flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 shrink-0 bg-[#0b0f19]/30">
                <span>Open Agent Kit © {new Date().getFullYear()} · MIT License</span>
                <span className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                    Open source, self-hosted, and yours to extend.
                </span>
            </footer>
        </div>
    );
};
