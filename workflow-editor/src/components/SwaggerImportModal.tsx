
import { useState } from 'react';
import { X, Search, Check, Loader2, Download } from 'lucide-react';
import { useLibraryStore } from '../stores/libraryStore';

interface SwaggerImportModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const SwaggerImportModal = ({ isOpen, onClose }: SwaggerImportModalProps) => {
    const { previewSwagger, importSwagger, isLoading } = useLibraryStore();
    const [url, setUrl] = useState('');
    const [step, setStep] = useState<'input' | 'preview'>('input');
    const [previewData, setPreviewData] = useState<any>(null);
    const [selectedEndpoints, setSelectedEndpoints] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);

    const handlePreview = async () => {
        if (!url) return;
        setError(null);
        try {
            const data = await previewSwagger(url);
            setPreviewData(data);
            // Select all by default
            setSelectedEndpoints((data.endpoints ?? []).map((endpoint: any) => endpoint.operation_id));
            setStep('preview');
        } catch (err) {
            setError((err as Error).message);
        }
    };

    const handleImport = async () => {
        if (selectedEndpoints.length === 0) return;
        try {
            await importSwagger(url, selectedEndpoints);
            onClose();
            // Reset state
            setStep('input');
            setUrl('');
            setPreviewData(null);
        } catch (err) {
            setError((err as Error).message);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[110] animate-in fade-in duration-200">
            <div className="bg-white rounded-xl shadow-2xl w-[600px] max-h-[80vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
                    <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                        <Download size={20} className="text-blue-600" />
                        Import Tools from Swagger
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-200 rounded">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 flex-1 overflow-y-auto">
                    {error && (
                        <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm border border-red-100">
                            {error}
                        </div>
                    )}

                    {step === 'input' ? (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Swagger / OpenAPI URL</label>
                                <input
                                    type="text"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    placeholder="https://api.example.com/openapi.json"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                                />
                                <p className="mt-1 text-xs text-gray-500">Provide a URL to a valid JSON OpenAPI specification.</p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="font-semibold text-gray-900">Select Tools to Import</h3>
                                <div className="text-sm text-gray-500">
                                    {selectedEndpoints.length} selected
                                </div>
                            </div>

                            <div className="border border-gray-200 rounded-lg max-h-[300px] overflow-y-auto">
                                {previewData?.endpoints.map((tool: any) => (
                                    <label key={tool.operation_id} className="flex items-start gap-3 p-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={selectedEndpoints.includes(tool.operation_id)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setSelectedEndpoints([...selectedEndpoints, tool.operation_id]);
                                                } else {
                                                    setSelectedEndpoints(selectedEndpoints.filter(id => id !== tool.operation_id));
                                                }
                                            }}
                                            className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                                        />
                                        <div>
                                            <div className="font-medium text-sm text-gray-900">{tool.name}</div>
                                            <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{tool.description}</div>
                                            <div className="mt-1 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-800 uppercase">
                                                {tool.method}
                                            </div>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-end gap-2">
                    {step === 'input' ? (
                        <>
                            <button onClick={onClose} className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 font-medium text-sm">Cancel</button>
                            <button
                                onClick={handlePreview}
                                disabled={!url || isLoading}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
                            >
                                {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
                                Preview
                            </button>
                        </>
                    ) : (
                        <>
                            <button onClick={() => setStep('input')} className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 font-medium text-sm">Back</button>
                            <button
                                onClick={handleImport}
                                disabled={selectedEndpoints.length === 0 || isLoading}
                                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
                            >
                                {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                                Import Selected
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};
