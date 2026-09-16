import { 
  FileText, 
  Activity, 
  Database,
  Plus
} from 'lucide-react';
import { Button } from '../components/ui/button';

export default function Dashboard() {
  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your knowledge base and recent activity.
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Knowledge Sources */}
        <div className="overflow-hidden rounded-lg bg-white shadow-sm border px-4 py-5 sm:p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 rounded-md bg-blue-50 p-3">
              <Database className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dt className="truncate text-sm font-medium text-gray-500">Knowledge Sources</dt>
              <dd className="mt-1 flex items-baseline text-gray-900">
                <span className="text-sm font-medium">Not connected</span>
              </dd>
            </div>
          </div>
        </div>

        {/* Total Documents */}
        <div className="overflow-hidden rounded-lg bg-white shadow-sm border px-4 py-5 sm:p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 rounded-md bg-green-50 p-3">
              <FileText className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dt className="truncate text-sm font-medium text-gray-500">Total Documents</dt>
              <dd className="mt-1 flex items-baseline text-gray-900">
                <span className="text-sm font-medium">No data yet</span>
              </dd>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="overflow-hidden rounded-lg bg-white shadow-sm border px-4 py-5 sm:p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0 rounded-md bg-purple-50 p-3">
              <Activity className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dt className="truncate text-sm font-medium text-gray-500">Weekly Activity</dt>
              <dd className="mt-1 flex items-baseline text-gray-900">
                <span className="text-sm font-medium">No activity yet</span>
              </dd>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Recent Knowledge Activity */}
        <div className="rounded-lg bg-white shadow-sm border">
          <div className="border-b border-gray-200 px-6 py-5 flex items-center justify-between">
            <h3 className="text-base font-medium leading-6 text-gray-900">Recent Knowledge Activity</h3>
            <Button className="text-sm bg-transparent text-gray-900 shadow-none hover:bg-gray-100">View all</Button>
          </div>
          <div className="px-6 py-12 flex flex-col items-center justify-center text-center">
            <Activity className="h-12 w-12 text-gray-300 mb-4" />
            <h4 className="text-sm font-medium text-gray-900">No activity yet</h4>
            <p className="mt-1 text-sm text-gray-500 max-w-sm">
              When users interact with your knowledge base or new information is ingested, it will appear here.
            </p>
          </div>
        </div>

        {/* Recent Documents */}
        <div className="rounded-lg bg-white shadow-sm border">
          <div className="border-b border-gray-200 px-6 py-5 flex items-center justify-between">
            <h3 className="text-base font-medium leading-6 text-gray-900">Recent Documents</h3>
            <Button className="text-sm bg-transparent text-gray-900 shadow-none hover:bg-gray-100">View all</Button>
          </div>
          <div className="px-6 py-12 flex flex-col items-center justify-center text-center">
            <FileText className="h-12 w-12 text-gray-300 mb-4" />
            <h4 className="text-sm font-medium text-gray-900">No recent documents</h4>
            <p className="mt-1 text-sm text-gray-500 max-w-sm">
              Upload documents or connect a data source to begin populating your knowledge base.
            </p>
            <div className="mt-6">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Document
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
