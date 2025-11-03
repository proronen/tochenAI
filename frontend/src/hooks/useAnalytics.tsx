import { useQuery } from "@tanstack/react-query";
import { AnalyticsService } from "../client";
import type { AnalyticsGetOverviewParams } from "../client/types.gen";

export const useAnalytics = (params: AnalyticsGetOverviewParams = {}) => {
    const overviewQuery = useQuery({
        queryKey: ["analytics", "overview", params.postedOnly, params.limit],
        queryFn: () => {
            return AnalyticsService.getAnalyticsOverview(params);
        },
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
    });

    return {
        overview: overviewQuery.data,

        isLoading: overviewQuery.isLoading,
        isFetching: overviewQuery.isFetching,
        isError: overviewQuery.isError,
        error: overviewQuery.error,

        refetch: overviewQuery.refetch,
    };
};
