import { useState, useEffect } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle2, Loader2, Clock, Archive, XCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { documentsApi } from '../features/documents/api/documentsApi';
import type { Document } from '../features/documents/types';
import clsx from 'clsx';

const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.pdf', '.docx', '.xlsx'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const fetchDocuments = async () => {
    try {
      const data = await documentsApi.getDocuments();
      setDocuments(data);
    } catch (error) {
      console.error('Failed to fetch documents', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0];
      setFile(selected);
      setUploadError(null);
      setUploadSuccess(false);

      // Auto-fill title if empty
      if (!title) {
        setTitle(selected.name.split('.').slice(0, -1).join('.'));
      }
    }
  };

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    setUploadError(null);
    setUploadSuccess(false);

    if (!title.trim()) {
      setUploadError('Please provide a title for the document.');
      return;
    }

    if (!file) {
      setUploadError('Please select a file to upload.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setUploadError('File size must not exceed 10 MB.');
      return;
    }

    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      setUploadError(`Unsupported file extension. Supported extensions are: ${SUPPORTED_EXTENSIONS.join(', ')}`);
      return;
    }

    setIsUploading(true);
    try {
      await documentsApi.uploadDocument(title, file);
      setUploadSuccess(true);
      setTitle('');
      setFile(null);

      // Reset file input visually
      const fileInput = document.getElementById('file-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

      await fetchDocuments();
    } catch (error: any) {
      setUploadError(
        error.response?.data?.file?.[0] ||
        error.response?.data?.detail ||
        'Failed to upload document. Please try again.'
      );
    } finally {
      setIsUploading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploaded':
        return <Clock className="h-4 w-4 text-gray-500" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'archived':
        return <Archive className="h-4 w-4 text-gray-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    return (
      <span className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium",
        {
          'bg-gray-100 text-gray-700': status === 'uploaded' || status === 'archived',
          'bg-blue-50 text-blue-700': status === 'processing',
          'bg-green-50 text-green-700': status === 'completed',
          'bg-red-50 text-red-700': status === 'failed',
        }
      )}>
        {getStatusIcon(status)}
        <span className="capitalize">{status}</span>
      </span>
    );
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Documents</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload, manage, and monitor your document ingestion.
        </p>
      </div>

      {/* Upload Section */}
      <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
        <div className="border-b px-6 py-4">
          <h2 className="text-lg font-medium text-gray-900">Upload Document</h2>
        </div>
        <div className="p-6">
          <form onSubmit={handleUpload} className="space-y-4">
            {uploadError && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-red-400" aria-hidden="true" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">{uploadError}</h3>
                  </div>
                </div>
              </div>
            )}

            {uploadSuccess && (
              <div className="rounded-md bg-green-50 p-4">
                <div className="flex">
                  <CheckCircle2 className="h-5 w-5 text-green-400" aria-hidden="true" />
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">Document uploaded successfully!</h3>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                  Document Title
                </label>
                <input
                  type="text"
                  name="title"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2"
                  placeholder="Enter a descriptive title"
                  disabled={isUploading}
                />
              </div>

              <div>
                <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700">
                  File
                </label>
                <div className="mt-1 flex items-center">
                  <input
                    id="file-upload"
                    name="file-upload"
                    type="file"
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-md p-0.5"
                    accept={SUPPORTED_EXTENSIONS.join(',')}
                    onChange={handleFileChange}
                    disabled={isUploading}
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Up to 10MB. Supported: {SUPPORTED_EXTENSIONS.join(', ')}
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isUploading || !file} className="bg-blue-600 text-white hover:bg-blue-700">
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>

      {/* Document List */}
      <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
        <div className="border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-medium text-gray-900">Your Documents</h2>
          <Button
            onClick={fetchDocuments}
            disabled={isLoading}
            className="text-sm border shadow-sm bg-white text-gray-700 hover:bg-gray-50 px-3"
          >
            Refresh
          </Button>
        </div>

        {isLoading ? (
          <div className="p-8 flex justify-center items-center">
            <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-300" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No documents</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by uploading your first document above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Document
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Size
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Chunks
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Uploaded
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <FileText className="flex-shrink-0 h-5 w-5 text-gray-400" />
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{doc.title}</div>
                          <div className="text-sm text-gray-500">{doc.file_type || 'Unknown type'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(doc.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {(doc.file_size / 1024).toFixed(1)} KB
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {doc.chunk_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
